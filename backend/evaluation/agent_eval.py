"""Agent 任务评测：路由/工具选择、参数、引用、转人工与成本。

设计取舍（刻意省 token）：
- 默认不调用外部模型：知识问答用本地检索 + 确定性假生成器。
  agent 指标（路由、工具选择、参数、转人工）不依赖生成质量；
  生成质量由 judge.py 抽样评测，检索质量由 enterprise_eval.py 用真实 BGE 单独评测。
- 需要真实生成时加 --use-real-model（会消耗 API token）。

用法：
    python -m evaluation.agent_eval                 # 全量 100 条
    python -m evaluation.agent_eval --tag smoke     # 25 条冒烟
    python -m evaluation.agent_eval --limit 20
    python -m evaluation.agent_eval --use-real-model --out report.json
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.chunking import Chunk
from app.embeddings import HashEmbedder, SentenceTransformerEmbedder
from app.generation import DeepSeekGenerator, GenerationResult
from app.retrieval import HybridRetriever
from app.workflow import run_tool_workflow

from app import config  # noqa: F401  加载 backend/.env（HF_HOME / HF_ENDPOINT 等）

from .enterprise_eval import build_evaluation_data

BASE_DIR = Path(__file__).resolve().parent
TAG_LIMITS = {"smoke": 25, "core": 60, "full": None}
KNOWLEDGE_ROUTES = {"faq", "knowledge_search"}


class DeterministicGenerator:
    """确定性假生成器：零 API 成本，保证评测可复现。"""

    def generate(self, question, contexts, history=None):
        text = f"根据资料：{contexts[0].text[:80]}"
        return GenerationResult(text=text, prompt_tokens=0, completion_tokens=0, total_tokens=0)


class EvalPipeline:
    """评测用的最小管线替身，只暴露工作流需要的两个入口。"""

    def __init__(self, retriever, generator) -> None:
        self.retriever = retriever
        self.generator = generator

    def retrieve(self, question, top_k=5, exclude_sources=None, tenant_id="default"):
        return self.retriever.search(
            question,
            top_k=top_k,
            exclude_sources=exclude_sources,
            tenant_id=tenant_id,
        )


def load_tasks() -> list[dict]:
    """合并 50 条新增 Agent 任务与 50 条知识问答任务。"""
    new_tasks = json.loads((BASE_DIR / "agent_tasks.json").read_text(encoding="utf-8"))["tasks"]
    corpus, questions = build_evaluation_data()
    knowledge_topics = {item["id"]: item["text"] for item in corpus}

    knowledge_tasks = []
    for index, item in enumerate(questions, start=1):
        expected_point = knowledge_topics[item["relevant_ids"][0]][:12]
        knowledge_tasks.append(
            {
                "id": f"k{index:02d}",
                "type": "knowledge",
                "question": item["question"],
                "expected_route": "knowledge",
                "must_escalate": False,
                "expect_keywords": [expected_point],
                # 知识类问题的措辞由 FAQ / 语料决定，不做强关键词匹配；
                # 其答案质量由引用准确率与 judge.py 的生成质量评测负责。
                "keywords_required": False,
            }
        )

    # 语料里这两条是"如何转人工"，但规则意图会把这类明确请求直接判为转人工并建单
    # （见 intent.py 的设计取舍），因此期望值同步为"应当转人工"。
    explicit_handoff = {"在哪里转人工？", "如何找人工？"}
    for task in knowledge_tasks:
        if task["question"] in explicit_handoff:
            task["must_escalate"] = True
    return new_tasks + knowledge_tasks


def build_pipeline(use_real_model: bool, use_real_embedder: bool) -> EvalPipeline:
    corpus, _ = build_evaluation_data()
    embedder = SentenceTransformerEmbedder() if use_real_embedder else HashEmbedder()
    retriever = HybridRetriever(embedder)
    if use_real_embedder:
        # 先预热模型：否则首次加载会被工具超时打断，评测结果和耗时都会失真。
        embedder.embed(["预热"])
    retriever.add_chunks([Chunk(text=item["text"], metadata={"id": item["id"]}) for item in corpus])
    generator = DeepSeekGenerator() if use_real_model else DeterministicGenerator()
    return EvalPipeline(retriever, generator)


def sample_tasks(tasks: list[dict], limit: int) -> list[dict]:
    """按类型轮流取样，保证小样本覆盖所有任务类型。"""
    by_type: dict[str, list[dict]] = {}
    for task in tasks:
        by_type.setdefault(task["type"], []).append(task)

    selected: list[dict] = []
    index = 0
    while len(selected) < limit:
        added = False
        for name in sorted(by_type):
            if index < len(by_type[name]) and len(selected) < limit:
                selected.append(by_type[name][index])
                added = True
        if not added:
            break
        index += 1
    return selected


def _predicted_route(outcome) -> str:
    """推导实际路由：FAQ > 业务工具 > 转人工。"""
    if any(step.get("action") == "faq" for step in outcome.steps):
        return "faq"

    def attempted(status: str | None) -> list[str]:
        return [
            step["tool"]
            for step in outcome.steps
            if step.get("tool")
            and step["tool"] != "human_handoff"
            and (status is None or step.get("status") == status)
        ]

    # 优先看成功的工具；全部失败时退回"尝试过的第一个"，避免把失败算成正确。
    successful = attempted("ok")
    if successful:
        return successful[0]
    failed = attempted(None)
    if failed:
        return failed[0]
    if outcome.handoff_reason:
        return "human_handoff"
    return "none"


def _route_matches(expected: str, predicted: str) -> bool:
    if expected == "knowledge":
        return predicted in KNOWLEDGE_ROUTES
    return expected == predicted


def evaluate_task(task: dict, pipeline: EvalPipeline) -> dict:
    outcome = run_tool_workflow(
        task["question"],
        pipeline=pipeline,
        tenant_id="default",
        session_id="agent-eval",
    )
    predicted = _predicted_route(outcome)
    answer = outcome.answer or ""
    escalated = outcome.handoff_reason is not None
    attempts = sum(int(step.get("attempts", 1) or 1) for step in outcome.steps if step.get("tool"))

    route_ok = _route_matches(task["expected_route"], predicted)
    keywords_list = task.get("expect_keywords", [])
    keywords_required = task.get("keywords_required", True)
    keyword_hit = any(word in answer for word in keywords_list) if keywords_list else True
    keywords_ok = all(word in answer for word in keywords_list) if keywords_required else True
    forbidden_hit = any(word in answer for word in task.get("forbid_keywords", []))
    escalate_ok = bool(task["must_escalate"]) == escalated
    citation_ok = None
    if task["expected_route"] in {"knowledge", "faq"} or task["type"] == "policy":
        citation_ok = len(outcome.citations) > 0 and keywords_ok

    expected_args = task.get("expected_args")
    argument_ok = None
    if expected_args:
        order_id = expected_args.get("order_id")
        argument_ok = any(
            step.get("input_summary") == order_id for step in outcome.steps if step.get("tool")
        )

    return {
        "id": task["id"],
        "type": task["type"],
        "question": task["question"],
        "expected_route": task["expected_route"],
        "predicted_route": predicted,
        "route_ok": route_ok,
        "argument_ok": argument_ok,
        "citation_ok": citation_ok,
        "must_escalate": bool(task["must_escalate"]),
        "escalated": escalated,
        "keywords_ok": keywords_ok,
        "keyword_hit": keyword_hit,
        "forbidden_hit": forbidden_hit,
        "task_success": route_ok and escalate_ok and keywords_ok and not forbidden_hit,
        "tool_calls": outcome.tool_calls,
        "attempts": attempts,
        "latency_ms": outcome.latency_ms,
        "total_tokens": (outcome.usage or {}).get("total_tokens", 0),
        "cost": outcome.cost or 0.0,
        "handoff_reason": outcome.handoff_reason,
    }


def _ratio(values: list[bool]) -> float:
    return round(sum(1 for item in values if item) / len(values), 4) if values else 0.0


def summarize(rows: list[dict]) -> dict:
    latencies = sorted(row["latency_ms"] for row in rows)
    escalated = [row for row in rows if row["escalated"]]
    should_escalate = [row for row in rows if row["must_escalate"]]
    should_answer = [row for row in rows if not row["must_escalate"]]
    citations = [row["citation_ok"] for row in rows if row["citation_ok"] is not None]
    arguments = [row["argument_ok"] for row in rows if row["argument_ok"] is not None]
    knowledge_rows = [row for row in rows if row["type"] == "knowledge"]

    def percentile(values: list[int], ratio: float) -> int:
        if not values:
            return 0
        index = min(len(values) - 1, int(len(values) * ratio))
        return values[index]

    return {
        "task_count": len(rows),
        "task_success_rate": _ratio([row["task_success"] for row in rows]),
        "route_accuracy": _ratio([row["route_ok"] for row in rows]),
        "tool_argument_accuracy": _ratio(arguments),
        "citation_accuracy": _ratio(citations),
        "knowledge_keyword_hit_rate": _ratio([row["keyword_hit"] for row in knowledge_rows]),
        "hallucination_rate": _ratio([row["forbidden_hit"] for row in rows]),
        "handoff_precision": _ratio([row["must_escalate"] for row in escalated]),
        "handoff_recall": _ratio([row["escalated"] for row in should_escalate]),
        "auto_resolve_rate": _ratio([not row["escalated"] for row in should_answer]),
        "avg_tool_calls": round(statistics.mean([row["tool_calls"] for row in rows]), 2) if rows else 0.0,
        "avg_retries": round(statistics.mean([max(row["attempts"] - 1, 0) for row in rows]), 2) if rows else 0.0,
        "latency_p50_ms": percentile(latencies, 0.5),
        "latency_p95_ms": percentile(latencies, 0.95),
        "total_tokens": sum(row["total_tokens"] for row in rows),
        "total_cost": round(sum(row["cost"] for row in rows), 6),
    }


def to_markdown(summary: dict, meta: dict) -> str:
    return "\n".join(
        [
            "# Agent 任务评测报告",
            "",
            f"- 任务数：{summary['task_count']}",
            f"- 生成方式：{meta['generator']}；嵌入：{meta['embedder']}",
            f"- 时间：{meta['created_at']}",
            "",
            "| 指标 | 数值 |",
            "| --- | --- |",
            f"| 任务成功率 | {summary['task_success_rate']:.2%} |",
            f"| 路由/工具选择准确率 | {summary['route_accuracy']:.2%} |",
            f"| 工具参数准确率 | {summary['tool_argument_accuracy']:.2%} |",
            f"| 引用准确率 | {summary['citation_accuracy']:.2%} |",
            f"| 知识问题文案命中率（参考） | {summary['knowledge_keyword_hit_rate']:.2%} |",
            f"| 违规/幻觉率 | {summary['hallucination_rate']:.2%} |",
            f"| 转人工 Precision | {summary['handoff_precision']:.2%} |",
            f"| 转人工 Recall | {summary['handoff_recall']:.2%} |",
            f"| 自动解决率 | {summary['auto_resolve_rate']:.2%} |",
            f"| 平均工具调用 | {summary['avg_tool_calls']} |",
            f"| 平均重试 | {summary['avg_retries']} |",
            f"| P50 / P95 延迟 | {summary['latency_p50_ms']} / {summary['latency_p95_ms']} ms |",
            f"| 总 token / 成本 | {summary['total_tokens']} / {summary['total_cost']} |",
        ]
    )


def run_evaluation(
    limit: int | None = None,
    tag: str = "full",
    use_real_model: bool = False,
    use_real_embedder: bool = False,
) -> dict:
    tasks = load_tasks()
    effective = TAG_LIMITS.get(tag) if tag in TAG_LIMITS else None
    if limit is not None:
        effective = limit
    if effective:
        tasks = sample_tasks(tasks, effective)

    # 评测按校准值开启相关性阈值，否则"答不出来"这条能力测不出来。
    previous_threshold = os.environ.get("RAG_MIN_SCORE")
    os.environ["RAG_MIN_SCORE"] = os.environ.get("EVAL_RAG_MIN_SCORE", "0.42")
    pipeline = build_pipeline(use_real_model, use_real_embedder)
    try:
        rows = [evaluate_task(task, pipeline) for task in tasks]
    finally:
        if previous_threshold is None:
            os.environ.pop("RAG_MIN_SCORE", None)
        else:
            os.environ["RAG_MIN_SCORE"] = previous_threshold
    summary = summarize(rows)
    meta = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tag": tag,
        "generator": "deepseek" if use_real_model else "deterministic-fake",
        "embedder": "bge-large-zh-v1.5" if use_real_embedder else "hash-embedder",
        "rag_min_score": os.environ.get("EVAL_RAG_MIN_SCORE", "0.42"),
        "note": "路由/工具指标不依赖生成质量；真实生成质量由 judge.py 抽样评测。",
    }
    return {"meta": meta, "summary": summary, "tasks": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent 任务评测")
    parser.add_argument("--tag", default="full", choices=sorted(TAG_LIMITS))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--use-real-model", action="store_true")
    parser.add_argument("--use-real-embedder", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    report = run_evaluation(
        limit=args.limit,
        tag=args.tag,
        use_real_model=args.use_real_model,
        use_real_embedder=args.use_real_embedder,
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = BASE_DIR / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else out_dir / f"agent-eval-{stamp}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    markdown = to_markdown(report["summary"], report["meta"])
    (out_dir / f"agent-eval-{stamp}.md").write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"\n报告已写入：{out_path}")


if __name__ == "__main__":
    main()

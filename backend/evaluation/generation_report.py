"""生成质量批量报告：用 LLM-as-Judge 给答案打 faithfulness / relevance。

设计（对应审计要求"LLM-as-Judge 必须定义 rubric，并抽样人工复核"）：
- rubric 写死在 `app/judge.py` 的提示词里：1.0 / 0.5 / 0.0 三档，含义明确；
- 每条任务先跑一次工作流拿到真实答案与引用，再让裁判打一次分，所以每题两次模型调用；
- 报告输出逐题分数、均值、低分清单，并额外导出**人工复核抽样表**（默认 10 条，留空列供人工填写）。

用法：
    python -m evaluation.generation_report --limit 20 --offline      # 抽样 20 条（约 ¥0.05）
    python -m evaluation.generation_report --tag core --offline      # 60 条
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

from app import config  # noqa: F401  加载 backend/.env
from app.judge import DeepSeekJudge

from .agent_eval import TAG_LIMITS, build_pipeline, load_tasks, sample_tasks
from .generation_eval import run_generation_evaluation

BASE_DIR = Path(__file__).resolve().parent
LOW_SCORE_THRESHOLD = 0.6


def build_cases(limit: int | None = None, tag: str = "smoke") -> list[dict]:
    """跑一遍工作流，收集「问题 / 答案 / 引用」作为裁判输入。"""
    tasks = load_tasks()
    effective = TAG_LIMITS.get(tag) if tag in TAG_LIMITS else None
    if limit is not None:
        effective = limit
    if effective:
        tasks = sample_tasks(tasks, effective)

    previous = os.environ.get("RAG_MIN_SCORE")
    os.environ["RAG_MIN_SCORE"] = os.environ.get("EVAL_RAG_MIN_SCORE", "0.42")
    try:
        pipeline = build_pipeline(use_real_model=True, use_real_embedder=True)
        from app.workflow import run_tool_workflow

        cases = []
        for task in tasks:
            outcome = run_tool_workflow(
                task["question"],
                pipeline=pipeline,
                tenant_id="default",
                session_id="generation-eval",
                history=task.get("history"),
            )
            cases.append(
                {
                    "id": task["id"],
                    "type": task["type"],
                    "question": task["question"],
                    "answer": outcome.answer,
                    "contexts": [citation.snippet for citation in outcome.citations],
                    # 只有走 DeepSeek 基于资料生成的答案才适合用 faithfulness / relevance 评分；
                    # 规则路径（FAQ 直答、工具直答、拒答、转人工）不适用，单独统计。
                    "route": outcome.model,
                    "generated": outcome.model == "knowledge_search+deepseek",
                }
            )
        return cases
    finally:
        if previous is None:
            os.environ.pop("RAG_MIN_SCORE", None)
        else:
            os.environ["RAG_MIN_SCORE"] = previous


def summarize_scores(rows: list[dict], threshold: float = LOW_SCORE_THRESHOLD) -> dict:
    """均值 + 低分清单：低分定义为任一维度低于阈值。"""
    if not rows:
        return {
            "case_count": 0,
            "faithfulness_mean": 0.0,
            "relevance_mean": 0.0,
            "low_score_count": 0,
            "low_score_rate": 0.0,
        }

    faithfulness = [row["faithfulness"] for row in rows]
    relevance = [row["relevance"] for row in rows]
    low = [row for row in rows if min(row["faithfulness"], row["relevance"]) < threshold]
    return {
        "case_count": len(rows),
        "faithfulness_mean": round(statistics.mean(faithfulness), 3),
        "relevance_mean": round(statistics.mean(relevance), 3),
        "low_score_count": len(low),
        "low_score_rate": round(len(low) / len(rows), 4),
        "low_score_cases": [
            {
                "id": row["id"],
                "type": row["type"],
                "question": row["question"],
                "faithfulness": row["faithfulness"],
                "relevance": row["relevance"],
                "answer": row["answer"][:120],
            }
            for row in low
        ],
    }


def to_markdown(summary: dict, meta: dict) -> str:
    excluded = meta.get("excluded_routes", {})
    lines = [
        "# 生成质量评估报告（LLM-as-Judge）",
        "",
        f"- 参与评分样本数：{summary['case_count']}（只统计由模型基于检索资料生成的答案）",
        f"- 总抽样：{meta.get('sampled', summary['case_count'])} 条；未参与评分（规则 / 工具 / 转人工路径）：{meta.get('excluded', 0)} 条",
        f"- 生成模型：{meta['model']}",
        f"- 时间：{meta['created_at']}",
        "- rubric：faithfulness 与 relevance 均按 1.0（完全有依据 / 直接回答）/ 0.5（部分）/ 0.0（编造 / 答非所问）三档打分",
        "- 口径说明：faithfulness 只对「依据资料生成」的答案有意义；FAQ 直答、订单/物流工具直答、拒答与转人工属于规则路径，"
        "用转人工 Precision/Recall 等 Agent 指标衡量，不纳入本报告。",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
        f"| faithfulness 均值 | {summary['faithfulness_mean']} |",
        f"| relevance 均值 | {summary['relevance_mean']} |",
        f"| 低分条数（任一维度 < {LOW_SCORE_THRESHOLD}） | {summary['low_score_count']}（{summary['low_score_rate']:.2%}） |",
    ]

    if excluded:
        lines += ["", "## 未参与评分的路径分布", ""]
        lines += ["| 路径 | 条数 |", "| --- | --- |"]
        for route, count in sorted(excluded.items(), key=lambda item: -item[1]):
            lines.append(f"| {route} | {count} |")

    if summary.get("low_score_cases"):
        lines += ["", "## 低分样本（需要人工复核）", ""]
        lines += ["| id | 类型 | 问题 | faithfulness | relevance | 答案摘录 |", "| --- | --- | --- | --- | --- | --- |"]
        for case in summary["low_score_cases"]:
            lines.append(
                f"| {case['id']} | {case['type']} | {case['question']} | "
                f"{case['faithfulness']} | {case['relevance']} | {case['answer']} |"
            )
    return "\n".join(lines)


def human_review_sheet(rows: list[dict], sample_size: int = 10) -> str:
    """导出人工复核抽样表：裁判分已填，人工列留空。"""
    sample = rows[:sample_size]
    lines = [
        "# 人工复核抽样表",
        "",
        "> 抽 10 条做人工复核：先看资料再看答案，独立打 1.0 / 0.5 / 0.0，"
        "与裁判分对比，偏差超过一档的记入结论。",
        "",
        "| id | 问题 | 答案 | 资料 | 裁判 faithfulness | 人工 faithfulness | 裁判 relevance | 人工 relevance |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in sample:
        contexts = " / ".join(case.get("contexts", []))[:200]
        answer = case["answer"].replace("\n", " ")[:200]
        lines.append(
            f"| {case['id']} | {case['question']} | {answer} | {contexts} | "
            f"{case.get('faithfulness', '')} |  | {case.get('relevance', '')} |  |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="生成质量批量评估")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--tag", default="smoke", choices=sorted(TAG_LIMITS))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

    print("① 跑工作流收集答案与引用…")
    cases = build_cases(limit=args.limit, tag=args.tag)
    scorable = [case for case in cases if case.get("generated")]
    excluded: dict[str, int] = {}
    for case in cases:
        if not case.get("generated"):
            excluded[case.get("route", "unknown")] = excluded.get(case.get("route", "unknown"), 0) + 1
    print(f"   收集到 {len(cases)} 条，其中 {len(scorable)} 条由模型基于资料生成（其余为规则/工具路径，不参与打分）")

    print("② 让裁判逐条打分（每条一次模型调用）…")
    result = run_generation_evaluation(scorable, DeepSeekJudge())

    summary = summarize_scores(result["per_case"])
    meta = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "deepseek-chat",
        "tag": args.tag,
        "limit": args.limit,
        "sampled": len(cases),
        "excluded": len(cases) - len(scorable),
        "excluded_routes": excluded,
    }

    report_dir = BASE_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    (report_dir / f"generation-report-{stamp}.json").write_text(
        json.dumps({"meta": meta, "summary": summary, "per_case": result["per_case"]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown = to_markdown(summary, meta)
    (report_dir / f"generation-report-{stamp}.md").write_text(markdown, encoding="utf-8")
    (report_dir / f"generation-review-{stamp}.md").write_text(
        human_review_sheet(result["per_case"]),
        encoding="utf-8",
    )

    print(markdown)
    print(f"\n报告：{report_dir / f'generation-report-{stamp}.md'}")
    print(f"人工复核抽样表：{report_dir / f'generation-review-{stamp}.md'}")


if __name__ == "__main__":
    main()

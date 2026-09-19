"""真实语料上的检索评测（文档级命中 + 证据级命中 + MRR）。

为什么要有这一套：`enterprise_eval` 跑的是 10 条短示例语料，句子短、一问一答
几乎一一对应，hit@1 = 0.96 说明不了长文档上的表现。这里直接在
`backend/corpus/` 的真实资料上跑，并且用两种口径区分"命中对的文档"和
"命中对的那句话"——后者才是能不能答对的关键。

用法（backend 目录下）：
    ..\\.venv\\Scripts\\python.exe -m evaluation.corpus_eval
    ..\\.venv\\Scripts\\python.exe -m evaluation.corpus_eval --embedder hash   # 快速自检
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.chunking import split_text, split_text_hierarchical
from app.evaluation import resolve_embedder
from app.retrieval import HybridRetriever
import os


def load_corpus(corpus_dir: Path) -> list[tuple[str, str]]:
    """读取语料：返回 (来源名, 正文)，README 只是说明文件，不入库。"""
    items: list[tuple[str, str]] = []
    for path in sorted(corpus_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        items.append((path.stem, path.read_text(encoding="utf-8")))
    return items


def build_retriever(
    corpus: list[tuple[str, str]],
    embedder,
    reranker=None,
) -> HybridRetriever:
    """按线上同一套切分与 id 规则建索引，保证评测口径和线上一致。"""
    hierarchical = os.getenv("HIERARCHICAL_CHUNKING", "false").lower() == "true"
    retriever = HybridRetriever(embedder, reranker=reranker)
    for source, text in corpus:
        pieces = split_text_hierarchical(text) if hierarchical else split_text(text)
        for index, piece in enumerate(pieces):
            piece.metadata["source"] = source
            piece.metadata["file_name"] = source
            piece.metadata["id"] = f"{source}-{index}"
        retriever.add_chunks(pieces)
    return retriever


def score_question(
    results,
    source: str,
    keyword: str,
    k_values: tuple[int, ...] = (1, 3, 5),
) -> dict[str, float]:
    """两种口径：doc_hit@k 只看文档对不对；evidence_hit@k 还要求那句证据出现。"""
    # 英文关键词大小写不敏感：语料里可能写成 nacos / Nacos、Spring Boot / SpringBoot
    needle = keyword.lower()
    metrics: dict[str, float] = {}
    for k in k_values:
        top = results[:k]
        metrics[f"doc_hit@{k}"] = float(
            any(item.metadata.get("source") == source for item in top)
        )
        metrics[f"evidence_hit@{k}"] = float(
            any(
                item.metadata.get("source") == source
                and needle in item.text.lower()
                for item in top
            )
        )

    reciprocal_rank = 0.0
    for index, item in enumerate(results, start=1):
        if item.metadata.get("source") == source and needle in item.text.lower():
            reciprocal_rank = 1.0 / index
            break
    metrics["evidence_mrr"] = reciprocal_rank
    return metrics


def run_corpus_evaluation(
    embedder,
    corpus_dir: Path | None = None,
    reranker=None,
) -> dict:
    base = Path(__file__).resolve().parent
    corpus = load_corpus(corpus_dir or (base.parent / "corpus"))
    questions = json.loads(
        (base / "corpus_eval_questions.json").read_text(encoding="utf-8")
    )["questions"]
    retriever = build_retriever(corpus, embedder, reranker=reranker)

    k_values = (1, 3, 5)
    per_query = []
    for item in questions:
        results = retriever.search(item["question"], top_k=max(k_values))
        metrics = score_question(results, item["source"], item["keyword"], k_values)
        per_query.append(
            {
                "question": item["question"],
                "expected_source": item["source"],
                "top1_source": results[0].metadata.get("source") if results else None,
                **metrics,
            }
        )

    average = {
        key: sum(row[key] for row in per_query) / len(per_query)
        for key in per_query[0]
        if key not in {"question", "expected_source", "top1_source"}
    }
    return {
        "corpus_size": len(corpus),
        "chunk_count": retriever.count(),
        "question_count": len(per_query),
        "average": average,
        "per_query": per_query,
    }


def render_report(result: dict) -> str:
    lines = [
        "# 真实语料检索评测",
        "",
        f"- 语料：{result['corpus_size']} 篇 / {result['chunk_count']} 个分块",
        f"- 问题：{result['question_count']} 条（每条标注期望文档 + 证据关键词）",
        f"- 时间：{datetime.now(timezone.utc).isoformat()}",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
    ]
    for key, value in result["average"].items():
        lines.append(f"| {key} | {value:.2f} |")

    lines += [
        "",
        "口径说明：`doc_hit@k` 只看 top-k 里有没有对的文档；`evidence_hit@k` 还要求",
        "命中那段里有标注的证据关键词（更接近「能不能答对」）。",
        "",
        "| 问题 | 期望文档 | 实际 top1 | doc@1 | evidence@1 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in result["per_query"]:
        mark = "" if row["evidence_hit@1"] else " ⚠"
        lines.append(
            f"| {row['question']}{mark} | {row['expected_source']} | "
            f"{row['top1_source']} | {row['doc_hit@1']:.0f} | {row['evidence_hit@1']:.0f} |"
        )
    return "\n".join(lines) + "\n"


def main(embedder_name: str = "bge") -> dict:
    result = run_corpus_evaluation(resolve_embedder(embedder_name))
    print(json.dumps(result["average"], ensure_ascii=False, indent=2))
    for row in result["per_query"]:
        if not row["evidence_hit@1"]:
            print(
                f"  未命中证据：{row['question']}（期望 {row['expected_source']}，"
                f"实际 top1 {row['top1_source']}）"
            )

    reports_dir = Path(__file__).resolve().parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = reports_dir / f"corpus-eval-{stamp}.md"
    path.write_text(render_report(result), encoding="utf-8")
    print(f"报告已写入：{path}")
    return result


def compare_rerank(embedder_name: str, rerank_model: str) -> dict:
    """A/B 对比开/关重排的效果与延迟，回答「rerank 到底提升多少」。"""
    from time import perf_counter

    from app.reranker import BGEReranker

    embedder = resolve_embedder(embedder_name)
    without = run_corpus_evaluation(embedder)
    # 重排模型首次加载很慢，先单独计时，避免把它算进检索延迟
    reranker = BGEReranker(rerank_model)
    started = perf_counter()
    reranker.rerank("预热", [])
    load_seconds = perf_counter() - started

    started = perf_counter()
    with_rerank = run_corpus_evaluation(
        resolve_embedder(embedder_name),
        reranker=reranker,
    )
    rerank_seconds = perf_counter() - started

    comparison = {
        "rerank_model": rerank_model,
        "model_load_seconds": round(load_seconds, 1),
        "without": without["average"],
        "with_rerank": with_rerank["average"],
        "delta": {
            key: round(
                with_rerank["average"][key] - without["average"][key], 3
            )
            for key in without["average"]
        },
        "with_rerank_total_seconds": round(rerank_seconds, 1),
        "question_count": with_rerank["question_count"],
    }
    return comparison


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="真实语料检索评测")
    parser.add_argument("--embedder", default="bge", choices=["bge", "hash"])
    parser.add_argument(
        "--compare-rerank",
        default=None,
        metavar="MODEL",
        help="给定时做重排 A/B 对比，例如 BAAI/bge-reranker-base",
    )
    args = parser.parse_args()
    if args.compare_rerank:
        print(
            json.dumps(
                compare_rerank(args.embedder, args.compare_rerank),
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        main(args.embedder)

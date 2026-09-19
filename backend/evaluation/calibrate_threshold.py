"""在真实语料上标定拒答阈值 RAG_MIN_SCORE。

为什么需要这个脚本：阈值是「域内问题的最低相似度」和「域外问题的最高相似度」
之间的一条线。换语料、换嵌入模型都会让这条线移动，所以它必须能复现，而不是
凭感觉填一个数。

用法（在 backend 目录下）：
    ..\\.venv\\Scripts\\python.exe -m evaluation.calibrate_threshold
    ..\\.venv\\Scripts\\python.exe -m evaluation.calibrate_threshold --embedder hash  # 快速自检
"""

import json
from pathlib import Path

from app.chunking import split_text
from app.evaluation import resolve_embedder
from app.retrieval import HybridRetriever


def load_corpus_texts(corpus_dir: Path) -> list[tuple[str, str]]:
    """读取语料目录下的 .md，返回 (来源名, 正文)；README 只是说明，不入库。"""
    items: list[tuple[str, str]] = []
    for path in sorted(corpus_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        items.append((path.stem, path.read_text(encoding="utf-8")))
    return items


def top_score(retriever: HybridRetriever, question: str, top_k: int = 5) -> float:
    """取一条问题在检索结果里的最高原始余弦相似度（阈值就是比这个值）。"""
    results = retriever.search(question, top_k=top_k)
    if not results:
        return 0.0
    return max(item.raw_dense_score for item in results)


def pick_threshold(
    relevant_scores: list[float],
    unrelated_scores: list[float],
) -> dict[str, float | bool | None]:
    """取两组分数的中点作为阈值；两组重叠时给出重叠区间并标记不可分。"""
    relevant_min = min(relevant_scores)
    unrelated_max = max(unrelated_scores)
    separable = relevant_min > unrelated_max
    return {
        "relevant_min": relevant_min,
        "unrelated_max": unrelated_max,
        "separable": separable,
        # 分不开时不给建议值：强行取中点会同时误伤相关问题和放过无关问题
        "threshold": round((relevant_min + unrelated_max) / 2, 4) if separable else None,
    }


def coverage(
    threshold: float,
    relevant_scores: list[float],
    unrelated_scores: list[float],
) -> dict[str, int]:
    """给定阈值时的保留/挡下数量，用来评估误伤与漏放的代价。"""
    return {
        "kept": sum(1 for score in relevant_scores if score >= threshold),
        "kept_total": len(relevant_scores),
        "blocked": sum(1 for score in unrelated_scores if score < threshold),
        "blocked_total": len(unrelated_scores),
    }


def build_retriever(corpus: list[tuple[str, str]], embedder) -> HybridRetriever:
    retriever = HybridRetriever(embedder)
    for source, text in corpus:
        # 与线上一致的段落切分；id 里带来源，避免不同资料的 id 撞车
        pieces = split_text(text)
        for index, piece in enumerate(pieces):
            piece.metadata["source"] = source
            piece.metadata["id"] = f"{source}-{index}"
        retriever.add_chunks(pieces)
    return retriever


def main(embedder_name: str = "bge") -> dict:
    base = Path(__file__).resolve().parent
    questions = json.loads(
        (base / "corpus_questions.json").read_text(encoding="utf-8")
    )
    corpus = load_corpus_texts(base.parent / "corpus")
    if not corpus:
        raise SystemExit("backend/corpus 下没有语料，先放几篇资料再标定")

    retriever = build_retriever(corpus, resolve_embedder(embedder_name))
    print(f"语料：{len(corpus)} 篇 / {retriever.count()} 个分块；嵌入：{embedder_name}")

    relevant_scores = [top_score(retriever, q) for q in questions["relevant"]]
    unrelated_scores = [top_score(retriever, q) for q in questions["unrelated"]]

    for question, score in zip(questions["relevant"], relevant_scores):
        print(f"  域内 {score:.3f}  {question}")
    for question, score in zip(questions["unrelated"], unrelated_scores):
        print(f"  域外 {score:.3f}  {question}")

    result = pick_threshold(relevant_scores, unrelated_scores)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["threshold"] is not None:
        print(json.dumps(coverage(result["threshold"], relevant_scores, unrelated_scores), ensure_ascii=False))
    else:
        print("警告：两组分数重叠，当前语料/模型下无法用单一阈值分开，需要补语料或换嵌入模型")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="标定 RAG_MIN_SCORE")
    parser.add_argument("--embedder", default="bge", choices=["bge", "hash"])
    main(parser.parse_args().embedder)

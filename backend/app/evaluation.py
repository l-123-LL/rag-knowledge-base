from collections.abc import Iterable

from . import config  # noqa: F401  加载 backend/.env（HF_HOME 等），保证能取到本地模型权重
from .chunking import Chunk
from .embeddings import HashEmbedder
from .retrieval import RetrievedChunk
from .retrieval import HybridRetriever


def resolve_embedder(name: str = "bge"):
    """按名称构造嵌入器。

    - `bge`：线上口径（BAAI/bge-large-zh-v1.5），命令行默认使用；
    - `hash`：测试替身，只用于快速回归，绝不能拿来对外报指标。
    """
    if name == "hash":
        return HashEmbedder()

    from .embeddings import SentenceTransformerEmbedder

    return SentenceTransformerEmbedder()


def hit_at_k(
    results: list[RetrievedChunk],
    relevant_ids: set[str],
    k: int,
) -> bool:
    top_ids = {chunk.metadata.get("id") for chunk in results[:k]}
    return bool(top_ids & relevant_ids)


def reciprocal_rank(
    results: list[RetrievedChunk],
    relevant_ids: set[str],
) -> float:
    for index, chunk in enumerate(results, start=1):
        if chunk.metadata.get("id") in relevant_ids:
            return 1.0 / index
    return 0.0


def evaluate_retrieval(
    results: list[RetrievedChunk],
    relevant_ids: Iterable[str],
    k_values: tuple[int, ...] = (1, 3, 5),
) -> dict[str, float]:
    relevant_set = set(relevant_ids)
    metrics = {
        f"hit@{k}": float(hit_at_k(results, relevant_set, k))
        for k in k_values
    }
    metrics["mrr"] = reciprocal_rank(results, relevant_set)
    return metrics


def run_retrieval_evaluation(
    corpus: list[dict],
    questions: list[dict],
    k_values: tuple[int, ...] = (1, 3, 5),
    embedder=None,
) -> dict:
    """跑一遍检索评估。

    `embedder` 不传时退回测试替身 HashEmbedder（仅用于单元测试）；
    命令行入口默认注入真实模型，保证对外指标与线上链路一致。
    """
    retriever = HybridRetriever(embedder or HashEmbedder())
    for item in corpus:
        retriever.add_chunks(
            [Chunk(text=item["text"], metadata={"id": item["id"]})]
        )

    per_query: list[dict[str, float]] = []
    for question in questions:
        results = retriever.search(
            question["question"],
            top_k=max(k_values),
        )
        per_query.append(
            evaluate_retrieval(
                results,
                question["relevant_ids"],
                k_values=k_values,
            )
        )

    if not per_query:
        return {"per_query": [], "average": {}}

    average = {
        key: sum(item[key] for item in per_query) / len(per_query)
        for key in per_query[0]
    }
    return {"per_query": per_query, "average": average}

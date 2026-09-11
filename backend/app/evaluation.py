from collections.abc import Iterable

from .retrieval import RetrievedChunk


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

from app.evaluation import evaluate_retrieval
from app.retrieval import RetrievedChunk


def test_evaluate_retrieval_scores_first_hit() -> None:
    results = [
        RetrievedChunk(text="目标资料", metadata={"id": "target"}),
        RetrievedChunk(text="其他资料", metadata={"id": "other"}),
    ]

    metrics = evaluate_retrieval(results, {"target"})

    assert metrics["hit@1"] == 1.0
    assert metrics["hit@3"] == 1.0
    assert metrics["mrr"] == 1.0


def test_evaluate_retrieval_scores_second_hit() -> None:
    results = [
        RetrievedChunk(text="干扰资料", metadata={"id": "noise"}),
        RetrievedChunk(text="目标资料", metadata={"id": "target"}),
    ]

    metrics = evaluate_retrieval(results, {"target"})

    assert metrics["hit@1"] == 0.0
    assert metrics["hit@3"] == 1.0
    assert metrics["mrr"] == 0.5


def test_evaluate_retrieval_returns_zero_for_missing_target() -> None:
    results = [RetrievedChunk(text="不相关资料", metadata={"id": "other"})]

    metrics = evaluate_retrieval(results, {"missing"})

    assert metrics["hit@1"] == 0.0
    assert metrics["mrr"] == 0.0

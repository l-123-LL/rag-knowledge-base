from app.evaluation import evaluate_retrieval, run_retrieval_evaluation
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


def test_run_retrieval_evaluation_returns_average_metrics() -> None:
    corpus = [
        {"id": "target", "text": "流感患者应尽早给予抗病毒治疗。"},
        {"id": "noise", "text": "高血压患者应低盐饮食。"},
    ]
    questions = [
        {"question": "流感抗病毒治疗", "relevant_ids": ["target"]},
    ]

    result = run_retrieval_evaluation(corpus, questions)

    assert result["average"]["hit@1"] == 1.0
    assert result["average"]["mrr"] == 1.0

from app.embeddings import HashEmbedder
from app.evaluation import evaluate_retrieval, resolve_embedder, run_retrieval_evaluation
from app.retrieval import RetrievedChunk


def test_resolve_embedder_hash_is_test_stub() -> None:
    # 测试替身必须能显式取到，避免评估误用成对外口径。
    assert isinstance(resolve_embedder("hash"), HashEmbedder)


def test_run_retrieval_evaluation_accepts_explicit_embedder() -> None:
    corpus = [{"id": "doc-1", "text": "退货政策：7 天内可申请无理由退货。"}]
    questions = [{"question": "退货要几天", "relevant_ids": ["doc-1"]}]

    result = run_retrieval_evaluation(
        corpus,
        questions,
        embedder=HashEmbedder(),
    )

    assert result["average"]["hit@1"] == 1.0


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
        {"id": "target", "text": "退款需在订单完成后 7 天内提交。"},
        {"id": "noise", "text": "物流用户应低盐饮食。"},
    ]
    questions = [
        {"question": "退款处理", "relevant_ids": ["target"]},
    ]

    result = run_retrieval_evaluation(corpus, questions)

    assert result["average"]["hit@1"] == 1.0
    assert result["average"]["mrr"] == 1.0

from app.embeddings import HashEmbedder
from app.generation import GenerationResult, Generator
from app.pipeline import RAGPipeline
from app.retrieval import RetrievedChunk


class FakeGenerator(Generator):
    def generate(
        self,
        question: str,
        contexts: list[RetrievedChunk],
        history: list[dict] | None = None,
    ) -> GenerationResult:
        return GenerationResult(
            text=f"根据资料回答：{contexts[0].text}",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )


def test_pipeline_ingests_and_answers() -> None:
    pipeline = RAGPipeline(HashEmbedder(), FakeGenerator())
    pipeline.ingest_text(
        "退款需在订单完成后 7 天内提交。",
        metadata={"file_name": "refund.txt"},
    )

    result = pipeline.answer("退款处理", top_k=1)

    assert "退款需在订单完成后 7 天内提交" in result.answer
    assert len(result.contexts) == 1


def test_pipeline_treats_low_relevance_as_insufficient() -> None:
    # 阈值默认关闭；开启后最高相似度不达标的检索结果按“资料不足”处理。
    pipeline = RAGPipeline(
        HashEmbedder(),
        FakeGenerator(),
        min_relevance_score=0.99,
    )
    pipeline.ingest_text(
        "发货时间以订单详情页显示为准。",
        metadata={"file_name": "shipping.txt"},
    )

    result = pipeline.answer("退款处理", top_k=1)

    assert result.contexts == []
    assert "资料不足" in result.answer


def test_pipeline_expands_child_hits_to_parent_context(
    monkeypatch,
) -> None:
    # 命中子块时，交给模型的是父块文本，避免答案被切分边界截断。
    monkeypatch.setenv("HIERARCHICAL_CHUNKING", "true")
    pipeline = RAGPipeline(HashEmbedder(), FakeGenerator())
    pipeline.ingest_text("退款需在订单完成后 7 天内提交。" * 30, metadata={"file_name": "refund.txt"})

    result = pipeline.answer("退款处理", top_k=1)

    assert result.contexts
    # FakeGenerator 会把拿到的 context 文本写进答案，父块比子块长
    assert len(result.answer) > len(result.contexts[0].text)

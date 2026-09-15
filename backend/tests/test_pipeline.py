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
        "流感患者应尽早给予抗病毒治疗。",
        metadata={"file_name": "flu.txt"},
    )

    result = pipeline.answer("流感抗病毒治疗", top_k=1)

    assert "尽早给予抗病毒治疗" in result.answer
    assert len(result.contexts) == 1


def test_pipeline_treats_low_relevance_as_insufficient() -> None:
    # 阈值默认关闭；开启后最高相似度不达标的检索结果按“资料不足”处理。
    pipeline = RAGPipeline(
        HashEmbedder(),
        FakeGenerator(),
        min_relevance_score=0.99,
    )
    pipeline.ingest_text(
        "高血压患者应低盐饮食并规律运动。",
        metadata={"file_name": "bp.txt"},
    )

    result = pipeline.answer("流感抗病毒治疗", top_k=1)

    assert result.contexts == []
    assert "资料不足" in result.answer

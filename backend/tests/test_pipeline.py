from app.embeddings import HashEmbedder
from app.generation import Generator
from app.pipeline import RAGPipeline
from app.retrieval import RetrievedChunk


class FakeGenerator(Generator):
    def generate(self, question: str, contexts: list[RetrievedChunk]) -> str:
        return f"根据资料回答：{contexts[0].text}"


def test_pipeline_ingests_and_answers() -> None:
    pipeline = RAGPipeline(HashEmbedder(), FakeGenerator())
    pipeline.ingest_text(
        "流感患者应尽早给予抗病毒治疗。",
        metadata={"file_name": "flu.txt"},
    )

    result = pipeline.answer("流感抗病毒治疗", top_k=1)

    assert "尽早给予抗病毒治疗" in result.answer
    assert len(result.contexts) == 1

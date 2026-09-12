from app.chunking import Chunk
from app.embeddings import HashEmbedder
from app.retrieval import HybridRetriever, RetrievedChunk


class FakeReranker:
    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        # 模拟精排：把包含“治疗”的片段排到最前。
        for chunk in chunks:
            chunk.combined_score = 1.0 if "治疗" in chunk.text else 0.0
        return sorted(chunks, key=lambda item: item.combined_score, reverse=True)


def test_reranker_changes_final_order() -> None:
    retriever = HybridRetriever(
        HashEmbedder(),
        reranker=FakeReranker(),
    )
    retriever.add_chunks(
        [
            Chunk(text="高血压患者应低盐饮食。"),
            Chunk(text="流感患者应尽早治疗。"),
        ]
    )

    results = retriever.search("高血压饮食", top_k=1)

    assert results[0].text == "流感患者应尽早治疗。"

from app.chunking import Chunk
from app.embeddings import HashEmbedder
from app.retrieval import HybridRetriever, RetrievedChunk


class FakeReranker:
    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        # 模拟精排：把包含“退款”的片段排到最前。
        for chunk in chunks:
            chunk.combined_score = 1.0 if "退款" in chunk.text else 0.0
        return sorted(chunks, key=lambda item: item.combined_score, reverse=True)


def test_reranker_changes_final_order() -> None:
    retriever = HybridRetriever(
        HashEmbedder(),
        reranker=FakeReranker(),
    )
    retriever.add_chunks(
        [
            Chunk(text="发货时间以订单详情页显示为准。"),
            Chunk(text="退款需商家审核后原路退回。"),
        ]
    )

    results = retriever.search("退款怎么处理", top_k=1)

    assert results[0].text == "退款需商家审核后原路退回。"

from app.chunking import Chunk
from app.embeddings import HashEmbedder
from app.retrieval import HybridRetriever


def test_hybrid_retriever_finds_relevant_chunk() -> None:
    retriever = HybridRetriever(HashEmbedder())
    retriever.add_chunks(
        [
            Chunk(text="退款需在订单完成后 7 天内提交。"),
            Chunk(text="发货时间以订单详情页显示为准。"),
            Chunk(text="发票信息需与订单抬头一致。"),
        ]
    )

    results = retriever.search("退款处理", top_k=1)

    assert results[0].text == "退款需在订单完成后 7 天内提交。"


def test_search_exposes_raw_dense_score_for_thresholds() -> None:
    # 归一化分数永远会有最大值 1.0，绝对阈值只能看原始余弦相似度。
    retriever = HybridRetriever(HashEmbedder())
    retriever.add_chunks(
        [
            Chunk(text="退款需在订单完成后 7 天内提交。"),
            Chunk(text="发货时间以订单详情页显示为准。"),
        ]
    )

    results = retriever.search("退款处理", top_k=2)

    assert results[0].raw_dense_score > 0.0
    assert results[0].raw_dense_score <= 1.0


def test_bm25_batch_scores_match_single_score() -> None:
    # 一次性打分是 O(N) 优化，结果必须与逐文档打分完全一致。
    retriever = HybridRetriever(HashEmbedder())
    retriever.add_chunks(
        [
            Chunk(text="退款需在订单完成后 7 天内提交。"),
            Chunk(text="发货时间以订单详情页显示为准。"),
        ]
    )

    values = retriever.bm25.scores("退款处理")

    assert len(values) == 2
    assert values[0] == retriever.bm25.score("退款处理", 0)
    assert values[1] == retriever.bm25.score("退款处理", 1)

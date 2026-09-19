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


def test_search_filters_by_effective_window() -> None:
    retriever = HybridRetriever(HashEmbedder())
    retriever.add_chunks(
        [
            Chunk(
                text="退款政策：7 天内可申请无理由退货。",
                metadata={"id": "old", "effective_to": "2026-01-31"},
            ),
            Chunk(
                text="退款政策：15 天内可申请无理由退货。",
                metadata={"id": "new", "effective_from": "2026-02-01"},
            ),
        ]
    )

    old_time = retriever.search("退款政策", top_k=5, as_of="2026-01-15")
    new_time = retriever.search("退款政策", top_k=5, as_of="2026-03-01")

    assert {item.metadata["id"] for item in old_time} == {"old"}
    assert {item.metadata["id"] for item in new_time} == {"new"}


def test_search_prefers_latest_version_for_same_doc_key() -> None:
    retriever = HybridRetriever(HashEmbedder())
    retriever.add_chunks(
        [
            Chunk(
                text="售后政策第 1 版：7 天无理由退货。",
                metadata={"id": "v1", "doc_key": "return-policy", "version": 1},
            ),
            Chunk(
                text="售后政策第 2 版：15 天无理由退货。",
                metadata={"id": "v2", "doc_key": "return-policy", "version": 2},
            ),
        ]
    )

    results = retriever.search("售后政策 退货", top_k=5)

    assert {item.metadata["id"] for item in results} == {"v2"}

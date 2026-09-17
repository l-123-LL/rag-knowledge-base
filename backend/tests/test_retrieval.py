from app.chunking import Chunk
from app.embeddings import HashEmbedder
from app.retrieval import HybridRetriever


def test_hybrid_retriever_finds_relevant_chunk() -> None:
    retriever = HybridRetriever(HashEmbedder())
    retriever.add_chunks(
        [
            Chunk(text="流感患者应尽早给予抗病毒治疗。"),
            Chunk(text="高血压患者应低盐饮食并规律运动。"),
            Chunk(text="用药前应核对药品说明书。"),
        ]
    )

    results = retriever.search("流感抗病毒治疗", top_k=1)

    assert results[0].text == "流感患者应尽早给予抗病毒治疗。"


def test_search_exposes_raw_dense_score_for_thresholds() -> None:
    # 归一化分数永远会有最大值 1.0，绝对阈值只能看原始余弦相似度。
    retriever = HybridRetriever(HashEmbedder())
    retriever.add_chunks(
        [
            Chunk(text="流感患者应尽早给予抗病毒治疗。"),
            Chunk(text="高血压患者应低盐饮食并规律运动。"),
        ]
    )

    results = retriever.search("流感抗病毒治疗", top_k=2)

    assert results[0].raw_dense_score > 0.0
    assert results[0].raw_dense_score <= 1.0


def test_bm25_batch_scores_match_single_score() -> None:
    # 一次性打分是 O(N) 优化，结果必须与逐文档打分完全一致。
    retriever = HybridRetriever(HashEmbedder())
    retriever.add_chunks(
        [
            Chunk(text="流感患者应尽早给予抗病毒治疗。"),
            Chunk(text="高血压患者应低盐饮食并规律运动。"),
        ]
    )

    values = retriever.bm25.scores("流感抗病毒")

    assert len(values) == 2
    assert values[0] == retriever.bm25.score("流感抗病毒", 0)
    assert values[1] == retriever.bm25.score("流感抗病毒", 1)

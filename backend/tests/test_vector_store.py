import json

import pytest

from app.vector_store import FAISSVectorStore


def test_faiss_vector_store_add_and_query() -> None:
    store = FAISSVectorStore(dimensions=4)
    store.add(
        id="refund",
        text="退款处理",
        embedding=[1.0, 0.0, 0.0, 0.0],
        metadata={"source": "售后政策"},
    )
    store.add(
        id="shipping",
        text="物流低盐饮食",
        embedding=[0.0, 1.0, 0.0, 0.0],
        metadata={"source": "物流指南"},
    )

    hits = store.query([1.0, 0.0, 0.0, 0.0], top_k=1)

    assert hits[0].id == "refund"


def test_faiss_query_scores_match_direct_dot_product() -> None:
    # 索引分数必须和「直接用记录里的向量做点积」完全一致，
    # 否则阈值判断和引用排序都会建立在错误分数上。
    store = FAISSVectorStore(dimensions=3)
    vectors = {
        "a": [0.6, 0.8, 0.0],
        "b": [0.0, 0.6, 0.8],
        "c": [0.8, 0.0, 0.6],
    }
    for key, vector in vectors.items():
        store.add(id=key, text=f"文本-{key}", embedding=vector)

    query = [0.5, 0.5, 0.5]
    hits = store.query(query, top_k=3)
    scores = {hit.id: hit.score for hit in hits}

    for key, vector in vectors.items():
        expected = sum(a * b for a, b in zip(query, vector))
        assert scores[key] == pytest.approx(expected, abs=1e-6)


def test_faiss_record_index_matches_all_records_order(tmp_path) -> None:
    # records.json 的键是字符串，读回来是字典序；记录顺序必须按内部 id 升序，
    # 否则「第 i 条分块」会拿到别人的分数（历史 bug：多条分块同一个常数分）。
    store = FAISSVectorStore(dimensions=2, persist_dir=tmp_path)
    for index in range(12):
        store.add(
            id=f"doc-{index}",
            text=f"第 {index} 条资料",
            embedding=[1.0, float(index) / 100],
        )
    store.save()

    reloaded = FAISSVectorStore(dimensions=2, persist_dir=tmp_path)

    assert [record.id for record in reloaded.all_records()] == [
        f"doc-{index}" for index in range(12)
    ]
    hits = reloaded.query([1.0, 0.0], top_k=12)
    assert sorted(hit.record_index for hit in hits) == list(range(12))
    # 原始 records.json 就是字典序键，确认测试真的覆盖了错位场景
    assert list(json.loads((tmp_path / "records.json").read_text(encoding="utf-8")))[
        :2
    ] == ["0", "1"]

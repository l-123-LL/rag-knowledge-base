from app.vector_store import FAISSVectorStore


def test_faiss_vector_store_add_and_query() -> None:
    store = FAISSVectorStore(dimensions=4)
    store.add(
        id="flu",
        text="流感抗病毒治疗",
        embedding=[1.0, 0.0, 0.0, 0.0],
        metadata={"source": "流感指南"},
    )
    store.add(
        id="hypertension",
        text="高血压低盐饮食",
        embedding=[0.0, 1.0, 0.0, 0.0],
        metadata={"source": "高血压指南"},
    )

    hits = store.query([1.0, 0.0, 0.0, 0.0], top_k=1)

    assert hits[0].id == "flu"

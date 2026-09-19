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

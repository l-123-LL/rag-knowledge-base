"""分块 id 撞车导致的向量分数错位回归测试。

历史 bug：两篇资料各自的分块 id 都从 `text-0` 开始，检索器用 `{id: 分数}`
回填分数时后面的记录覆盖前面的，多条分块拿到同一个常数分，正确答案反而被
阈值判断成「资料不足」。
"""

import math

import pytest

from app.chunking import Chunk
from app.generation import GenerationResult, Generator
from app.pipeline import RAGPipeline
from app.retrieval import HybridRetriever, RetrievedChunk
from app.vector_store import InMemoryVectorStore


class CharVectorEmbedder:
    """字符袋向量：相似度只取决于字符重叠，方便在测试里独立算期望分数。"""

    def __init__(self, size: int = 64) -> None:
        self.size = size

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.size
            for char in text:
                vector[ord(char) % self.size] += 1.0
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append([value / norm for value in vector])
        return vectors


class FakeGenerator(Generator):
    def generate(
        self,
        question: str,
        contexts: list[RetrievedChunk],
        history: list[dict] | None = None,
    ) -> GenerationResult:
        return GenerationResult(text=contexts[0].text, prompt_tokens=1, completion_tokens=1, total_tokens=2)


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def test_dense_scores_survive_duplicate_chunk_ids() -> None:
    embedder = CharVectorEmbedder()
    texts = [
        ("甲", "快递签收前可以先验收再签收。"),
        ("甲", "退货需在签收后七天内在订单页申请。"),
        ("乙", "发票抬头需与订单信息保持一致。"),
        ("乙", "物流时效以订单详情页显示的信息为准。"),
    ]
    # 直接往向量库里塞重复 id，模拟「修复前已经建好的历史索引」
    store = InMemoryVectorStore()
    for position, (source, text) in enumerate(texts):
        chunk_id = f"text-{position % 2}"
        store.add(
            id=chunk_id,
            text=text,
            embedding=embedder.embed([text])[0],
            metadata={"id": chunk_id, "source": source},
        )
    retriever = HybridRetriever(embedder, vector_store=store)

    assert len(retriever.doc_ids) == 4  # 四条分块都在
    assert len(set(retriever.doc_ids)) == 2  # 但 id 确实只用了两个（历史索引状态）

    query = "签收前可以先验收吗"
    results = retriever.search(query, top_k=4)

    # 期望分数用「查询与文本的余弦相似度」独立算出来，不复用检索器内部实现
    query_vector = embedder.embed([query])[0]
    expected = {
        text: _cosine(query_vector, embedder.embed([text])[0]) for _, text in texts
    }

    assert results[0].text == "快递签收前可以先验收再签收。"
    for item in results:
        assert item.raw_dense_score == pytest.approx(expected[item.text], abs=1e-5)


def test_ingest_assigns_unique_chunk_ids_across_documents() -> None:
    pipeline = RAGPipeline(CharVectorEmbedder(), FakeGenerator())
    for source in ("doc-a", "doc-b", "doc-c"):
        pipeline.ingest_text(
            "快递签收前可以先验收再签收。",
            metadata={"source": source},
        )

    ids = [metadata["id"] for metadata in pipeline.retriever.doc_metadata]

    assert len(ids) == len(set(ids)) == 3


def test_duplicate_chunk_ids_are_skipped_on_ingest() -> None:
    retriever = HybridRetriever(CharVectorEmbedder())
    chunk = Chunk(text="快递签收前可以先验收再签收。", metadata={"id": "same-id"})

    assert retriever.add_chunks([chunk]) == 1
    assert retriever.add_chunks([chunk]) == 0
    assert retriever.count() == 1


def test_reingesting_same_document_is_idempotent() -> None:
    pipeline = RAGPipeline(CharVectorEmbedder(), FakeGenerator())
    text = "快递签收前可以先验收再签收。\n\n退货需在签收后七天内申请。"

    first = pipeline.ingest_text(text, metadata={"source": "doc-a"})
    second = pipeline.ingest_text(text, metadata={"source": "doc-a"})

    assert first == 2
    assert second == 0
    assert pipeline.chunk_count() == 2

import math
from dataclasses import dataclass, field

import jieba
from rank_bm25 import BM25Okapi

from .chunking import Chunk
from .embeddings import Embedder
from .vector_store import InMemoryVectorStore, VectorStore


@dataclass
class RetrievedChunk:
    text: str
    metadata: dict = field(default_factory=dict)
    dense_score: float = 0.0
    # 归一化前的原始余弦相似度，用于绝对阈值判断（归一化分数永远有最大值 1.0）
    raw_dense_score: float = 0.0
    bm25_score: float = 0.0
    combined_score: float = 0.0
    rerank_score: float = 0.0

    def __init__(
        self,
        text: str,
        metadata: dict | None = None,
        dense_score: float = 0.0,
        raw_dense_score: float = 0.0,
        bm25_score: float = 0.0,
        combined_score: float = 0.0,
        rerank_score: float = 0.0,
    ) -> None:
        self.text = text
        self.metadata = metadata or {}
        self.dense_score = dense_score
        self.raw_dense_score = raw_dense_score
        self.bm25_score = bm25_score
        self.combined_score = combined_score
        self.rerank_score = rerank_score


def _tokenize(text: str) -> list[str]:
    """用 jieba 做中文分词，保留英文和数字。"""
    return [token.strip() for token in jieba.cut(text.lower()) if token.strip()]


class BM25Index:
    def __init__(self) -> None:
        self.documents: list[list[str]] = []
        self._model: BM25Okapi | None = None

    def add_document(self, text: str) -> None:
        self.documents.append(_tokenize(text))
        self._model = None

    def finalize(self) -> None:
        if self.documents and self._model is None:
            self._model = BM25Okapi(self.documents)

    def score(self, query: str, document_index: int) -> float:
        """单文档打分（保留原签名，内部改为复用一次性打分结果）。"""
        values = self.scores(query)
        if document_index >= len(values):
            return 0.0
        return values[document_index]

    def scores(self, query: str) -> list[float]:
        """一次算完全量 BM25 分数。

        原实现每个候选都调用一次 model.get_scores()，等于对每篇文档重算全库分数，
        复杂度 O(N²)；实测 512 篇文档时循环打分 88.3 ms、一次性打分 0.38 ms。
        """
        self.finalize()
        if self._model is None:
            return [0.0] * len(self.documents)
        return [float(value) for value in self._model.get_scores(_tokenize(query))]


class HybridRetriever:
    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore | None = None,
        dense_weight: float = 0.7,
        reranker=None,
        rerank_top_k: int = 20,
    ) -> None:
        self.embedder = embedder
        self.dense_weight = dense_weight
        self.reranker = reranker
        self.rerank_top_k = rerank_top_k
        self.vector_store = vector_store or InMemoryVectorStore()
        self.bm25 = BM25Index()
        self.doc_ids: list[str] = []
        self.doc_texts: list[str] = []
        self.doc_metadata: list[dict] = []
        self._load_existing_records()

    def _load_existing_records(self) -> None:
        for record in self.vector_store.all_records():
            self.bm25.add_document(record.text)
            self.doc_ids.append(record.id)
            self.doc_texts.append(record.text)
            self.doc_metadata.append(record.metadata)
        self.bm25.finalize()

    def add_chunks(self, chunks: list[Chunk]) -> None:
        embeddings = self.embedder.embed([chunk.text for chunk in chunks])

        for chunk, embedding in zip(chunks, embeddings):
            document_id = chunk.metadata.get("id", chunk.text[:40])
            self.vector_store.add(
                id=document_id,
                text=chunk.text,
                embedding=embedding,
                metadata=chunk.metadata,
            )
            self.bm25.add_document(chunk.text)
            self.doc_ids.append(document_id)
            self.doc_texts.append(chunk.text)
            self.doc_metadata.append(chunk.metadata)

        self.bm25.finalize()

    def count(self) -> int:
        return len(self.doc_ids)

    def search(
        self,
        query: str,
        top_k: int = 5,
        exclude_sources: set[str] | None = None,
        tenant_id: str = "default",
    ) -> list[RetrievedChunk]:
        query_embedding = self.embedder.embed([query])[0]
        vector_hits = self.vector_store.query(query_embedding, top_k=len(self.doc_ids))
        dense_by_id = {hit.id: hit.score for hit in vector_hits}
        dense_scores = [dense_by_id.get(document_id, 0.0) for document_id in self.doc_ids]
        dense_min, dense_max = min(dense_scores), max(dense_scores)
        dense_range = dense_max - dense_min or 1.0

        # 一次性取回全量 BM25 分数，避免逐文档重复计算。
        bm25_scores = self.bm25.scores(query)
        bm25_min, bm25_max = min(bm25_scores), max(bm25_scores)
        bm25_range = bm25_max - bm25_min or 1.0

        candidates: list[RetrievedChunk] = []
        for index, document_id in enumerate(self.doc_ids):
            dense_score = (dense_scores[index] - dense_min) / dense_range
            bm25_score = (bm25_scores[index] - bm25_min) / bm25_range
            candidates.append(
                RetrievedChunk(
                    text=self.doc_texts[index],
                    metadata=self.doc_metadata[index],
                    dense_score=dense_score,
                    raw_dense_score=dense_scores[index],
                    bm25_score=bm25_score,
                    combined_score=(
                        self.dense_weight * dense_score
                        + (1 - self.dense_weight) * bm25_score
                    ),
                )
            )

        excluded = exclude_sources or set()
        candidates = [
            candidate
            for candidate in candidates
            if candidate.metadata.get("source") not in excluded
            and candidate.metadata.get("tenant_id", "default") == tenant_id
        ]
        candidates.sort(
            key=lambda item: item.combined_score,
            reverse=True,
        )
        candidates = candidates[: self.rerank_top_k]
        if self.reranker is not None:
            candidates = self.reranker.rerank(query, candidates)
        return candidates[:top_k]

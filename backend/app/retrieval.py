from dataclasses import dataclass, field
from datetime import UTC, datetime

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
        # 已入库的分块 id，用于「同一份资料重复导入」去重（幂等导入）。
        self._known_ids: set[str] = set()
        self._load_existing_records()

    def _load_existing_records(self) -> None:
        for record in self.vector_store.all_records():
            self.bm25.add_document(record.text)
            self.doc_ids.append(record.id)
            self.doc_texts.append(record.text)
            self.doc_metadata.append(record.metadata)
            self._known_ids.add(record.id)
        self.bm25.finalize()

    def add_chunks(self, chunks: list[Chunk]) -> int:
        """写入分块，返回真正新增的数量（重复 id 会被跳过）。"""
        fresh: list[Chunk] = []
        for chunk in chunks:
            declared_id = chunk.metadata.get("id")
            # 只有显式声明了 id 的分块才做去重，避免把「前 40 字相同」的
            # 不同段落误判成同一块。
            if declared_id and declared_id in self._known_ids:
                continue
            fresh.append(chunk)

        if not fresh:
            return 0

        chunks = fresh
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
            self._known_ids.add(document_id)

        self.bm25.finalize()
        return len(chunks)

    def count(self) -> int:
        return len(self.doc_ids)

    def _align_dense_scores(self, vector_hits) -> list[float]:
        """把向量库返回的分数对齐到 doc_ids 的顺序。

        历史实现直接按分块 id 建字典 `{id: score}`，一旦两篇资料的分块 id 撞车
        （例如都叫 `text-0`），后面的记录会覆盖前面的，导致多条分块拿到同一个
        常数分数、阈值判断跟着失效。这里优先用存储内部唯一下标对齐；下标不连续
        （外部索引）时退回按 id 取最大分，至少不会拿到别人的低分。
        """
        if not vector_hits:
            return [0.0] * len(self.doc_ids)

        has_indices = all(hit.record_index is not None for hit in vector_hits)
        indices = {hit.record_index for hit in vector_hits}
        if has_indices and indices == set(range(len(self.doc_ids))):
            by_index = {hit.record_index: hit.score for hit in vector_hits}
            return [by_index[index] for index in range(len(self.doc_ids))]

        by_id: dict[str, float] = {}
        for hit in vector_hits:
            by_id[hit.id] = max(by_id.get(hit.id, float("-inf")), hit.score)
        return [by_id.get(document_id, 0.0) for document_id in self.doc_ids]

    def search(
        self,
        query: str,
        top_k: int = 5,
        exclude_sources: set[str] | None = None,
        tenant_id: str = "default",
        as_of: str | None = None,
    ) -> list[RetrievedChunk]:
        query_embedding = self.embedder.embed([query])[0]
        vector_hits = self.vector_store.query(query_embedding, top_k=len(self.doc_ids))
        dense_scores = self._align_dense_scores(vector_hits)
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
            and self._is_effective(candidate.metadata, as_of)
        ]
        candidates = self._prefer_latest_version(candidates)
        candidates.sort(
            key=lambda item: item.combined_score,
            reverse=True,
        )
        candidates = candidates[: self.rerank_top_k]
        if self.reranker is not None:
            candidates = self.reranker.rerank(query, candidates)
        return candidates[:top_k]

    @staticmethod
    def _is_effective(metadata: dict, as_of: str | None) -> bool:
        """按生效时间窗口过滤：metadata 可带 effective_from / effective_to（ISO 日期）。"""
        moment = as_of or datetime.now(UTC).date().isoformat()
        start = metadata.get("effective_from")
        end = metadata.get("effective_to")

        # 还没生效，或已经失效，都不该被召回
        starts_in_future = bool(start) and str(start)[:10] > moment[:10]
        already_expired = bool(end) and str(end)[:10] < moment[:10]
        return not (starts_in_future or already_expired)

    @staticmethod
    def _prefer_latest_version(candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """同一 doc_key 的多个版本只保留版本号最高的，避免新旧政策同时命中。"""
        latest: dict[str, float] = {}
        for candidate in candidates:
            key = candidate.metadata.get("doc_key")
            if not key:
                continue
            version = float(candidate.metadata.get("version") or 0)
            if key not in latest or version > latest[key]:
                latest[key] = version

        kept: list[RetrievedChunk] = []
        for candidate in candidates:
            key = candidate.metadata.get("doc_key")
            if not key:
                kept.append(candidate)
                continue
            if float(candidate.metadata.get("version") or 0) >= latest[key]:
                kept.append(candidate)
        return kept

import math
from dataclasses import dataclass, field

from .chunking import Chunk
from .embeddings import Embedder, tokenize
from .vector_store import InMemoryVectorStore, VectorHit


@dataclass
class RetrievedChunk:
    text: str
    metadata: dict = field(default_factory=dict)
    dense_score: float = 0.0
    bm25_score: float = 0.0
    combined_score: float = 0.0


class SimpleBM25:
    """轻量 BM25，先保证关键词精确命中，后续可换成 rank-bm25。"""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.documents: list[list[str]] = []
        self.doc_freq: dict[str, int] = {}
        self.doc_lengths: list[int] = []
        self.avg_doc_length = 0.0

    def add_document(self, text: str) -> None:
        tokens = tokenize(text)
        self.documents.append(tokens)
        self.doc_lengths.append(len(tokens))

        for token in set(tokens):
            self.doc_freq[token] = self.doc_freq.get(token, 0) + 1

        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths)

    def score(self, query: str, document_index: int) -> float:
        query_tokens = tokenize(query)
        doc_tokens = self.documents[document_index]
        doc_len = self.doc_lengths[document_index]
        total = 0.0

        for token in query_tokens:
            freq = doc_tokens.count(token)
            if freq == 0:
                continue

            df = self.doc_freq.get(token, 0)
            idf = math.log(
                1 + (len(self.documents) - df + 0.5) / (df + 0.5)
            )
            total += (
                idf
                * freq
                * (self.k1 + 1)
                / (
                    freq
                    + self.k1
                    * (1 - self.b + self.b * doc_len / self.avg_doc_length)
                )
            )

        return total


class HybridRetriever:
    def __init__(
        self,
        embedder: Embedder,
        dense_weight: float = 0.7,
    ) -> None:
        self.embedder = embedder
        self.dense_weight = dense_weight
        self.vector_store = InMemoryVectorStore()
        self.bm25 = SimpleBM25()
        self.doc_ids: list[str] = []
        self.doc_texts: list[str] = []
        self.doc_metadata: list[dict] = []

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

    def search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        query_embedding = self.embedder.embed([query])[0]
        vector_hits = self.vector_store.query(query_embedding, top_k=len(self.doc_ids))
        dense_by_id = {hit.id: hit.score for hit in vector_hits}
        dense_scores = [dense_by_id.get(document_id, 0.0) for document_id in self.doc_ids]
        dense_min, dense_max = min(dense_scores), max(dense_scores)
        dense_range = dense_max - dense_min or 1.0

        bm25_scores = [self.bm25.score(query, index) for index in range(len(self.doc_ids))]
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
                    bm25_score=bm25_score,
                    combined_score=(
                        self.dense_weight * dense_score
                        + (1 - self.dense_weight) * bm25_score
                    ),
                )
            )

        candidates.sort(
            key=lambda item: item.combined_score,
            reverse=True,
        )
        return candidates[:top_k]

from typing import Protocol

from .retrieval import RetrievedChunk


class Reranker(Protocol):
    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """对候选片段重新打分并排序。"""


class BGEReranker:
    """使用开源 BGE reranker 模型做精排；首次使用时才加载模型。"""

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3") -> None:
        self.model_name = model_name
        self._model = None

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)

        pairs = [(query, chunk.text) for chunk in chunks]
        scores = self._model.predict(pairs)
        for chunk, score in zip(chunks, scores):
            chunk.rerank_score = float(score)
            chunk.combined_score = float(score)

        chunks.sort(key=lambda chunk: chunk.combined_score, reverse=True)
        return chunks

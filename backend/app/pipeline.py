from dataclasses import dataclass

from .chunking import Chunk, split_text
from .embeddings import Embedder
from .generation import Generator, GenerationResult
from .retrieval import HybridRetriever, RetrievedChunk
from .vector_store import VectorStore


@dataclass
class PipelineAnswer:
    answer: str
    contexts: list[RetrievedChunk]
    usage: dict[str, int] | None = None


class RAGPipeline:
    def __init__(
        self,
        embedder: Embedder,
        generator: Generator,
        vector_store: VectorStore | None = None,
        reranker=None,
        min_relevance_score: float = 0.0,
    ) -> None:
        self.retriever = HybridRetriever(
            embedder,
            vector_store=vector_store,
            reranker=reranker,
        )
        self.generator = generator
        # 原始余弦相似度阈值；默认 0 表示不启用，避免小语料上误判为资料不足。
        self.min_relevance_score = min_relevance_score

    def ingest_text(self, text: str, metadata: dict | None = None) -> int:
        chunks = split_text(text)
        for index, chunk in enumerate(chunks):
            chunk.metadata.update(metadata or {})
            chunk.metadata["chunk_index"] = index
            chunk.metadata.setdefault("id", f"{metadata.get('file_name', 'text')}-{index}")

        self.retriever.add_chunks(chunks)
        save = getattr(self.retriever.vector_store, "save", None)
        if save is not None:
            save()
        return len(chunks)

    def answer(
        self,
        question: str,
        top_k: int = 5,
        history: list[dict] | None = None,
        exclude_sources: set[str] | None = None,
        tenant_id: str = "default",
    ) -> PipelineAnswer:
        contexts = self.retrieve(
            question,
            top_k=top_k,
            exclude_sources=exclude_sources,
            tenant_id=tenant_id,
        )
        # 检索为空或相似度低于阈值都按“资料不足”处理，由接口层引导转人工。
        if not contexts or self.is_below_threshold(contexts):
            return PipelineAnswer(
                answer="当前资料不足，暂时无法给出可靠回答。",
                contexts=[],
            )

        result: GenerationResult = self.generator.generate(
            question,
            contexts,
            history=history,
        )
        return PipelineAnswer(
            answer=result.text,
            contexts=contexts,
            usage={
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
            },
        )

    def is_below_threshold(self, contexts: list[RetrievedChunk]) -> bool:
        """按归一化前的余弦相似度判断是否真的没有相关资料。"""
        if self.min_relevance_score <= 0 or not contexts:
            return False

        return max(item.raw_dense_score for item in contexts) < self.min_relevance_score

    def retrieve(
        self,
        question: str,
        top_k: int = 5,
        exclude_sources: set[str] | None = None,
        tenant_id: str = "default",
    ) -> list[RetrievedChunk]:
        contexts = self.retriever.search(
            question,
            top_k=top_k,
            exclude_sources=exclude_sources,
            tenant_id=tenant_id,
        )
        return contexts

    def chunk_count(self) -> int:
        return self.retriever.count()

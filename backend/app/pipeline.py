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
    ) -> None:
        self.retriever = HybridRetriever(
            embedder,
            vector_store=vector_store,
            reranker=reranker,
        )
        self.generator = generator

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
    ) -> PipelineAnswer:
        contexts = self.retrieve(question, top_k=top_k)
        if not contexts:
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

    def retrieve(self, question: str, top_k: int = 5) -> list[RetrievedChunk]:
        contexts = self.retriever.search(question, top_k=top_k)
        return contexts

    def chunk_count(self) -> int:
        return self.retriever.count()

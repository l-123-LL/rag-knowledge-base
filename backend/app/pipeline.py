from dataclasses import dataclass

from .chunking import Chunk, split_text
from .embeddings import Embedder
from .generation import Generator
from .retrieval import HybridRetriever, RetrievedChunk
from .vector_store import VectorStore


@dataclass
class PipelineAnswer:
    answer: str
    contexts: list[RetrievedChunk]


class RAGPipeline:
    def __init__(
        self,
        embedder: Embedder,
        generator: Generator,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.retriever = HybridRetriever(embedder, vector_store=vector_store)
        self.generator = generator

    def ingest_text(self, text: str, metadata: dict | None = None) -> int:
        chunks = split_text(text)
        for index, chunk in enumerate(chunks):
            chunk.metadata.update(metadata or {})
            chunk.metadata["chunk_index"] = index
            chunk.metadata.setdefault("id", f"{metadata.get('file_name', 'text')}-{index}")

        self.retriever.add_chunks(chunks)
        return len(chunks)

    def answer(self, question: str, top_k: int = 5) -> PipelineAnswer:
        contexts = self.retriever.search(question, top_k=top_k)
        if not contexts:
            return PipelineAnswer(
                answer="当前资料不足，暂时无法给出可靠回答。",
                contexts=[],
            )

        answer = self.generator.generate(question, contexts)
        return PipelineAnswer(answer=answer, contexts=contexts)

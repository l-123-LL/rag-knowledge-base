import hashlib
import os
from dataclasses import dataclass

from .chunking import split_text, split_text_hierarchical
from .embeddings import Embedder
from .followup import build_retrieval_query
from .generation import GenerationResult, Generator
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
        metadata = metadata or {}
        # 可选父子切分：命中子块、生成时用父块上下文（HIERARCHICAL_CHUNKING=true 开启）。
        hierarchical = os.getenv("HIERARCHICAL_CHUNKING", "false").lower() == "true"
        chunks = split_text_hierarchical(text) if hierarchical else split_text(text)
        # 分块 id 必须全局唯一。早期实现是 f"text-{index}"，多篇资料导入时 id 互相
        # 撞车，检索阶段按 id 回填向量分数会互相覆盖，导致正确答案被判定为「资料不足」。
        # 现在用「来源 + 序号 + 内容摘要」拼 id：既唯一，又能在内容不变时保持稳定（可重复导入去重）。
        source_key = (
            metadata.get("doc_key")
            or metadata.get("file_name")
            or metadata.get("source")
            or "text"
        )
        for index, chunk in enumerate(chunks):
            chunk.metadata.update(metadata)
            chunk.metadata["chunk_index"] = index
            digest = hashlib.sha1(chunk.text.encode("utf-8")).hexdigest()[:8]
            chunk.metadata.setdefault("id", f"{source_key}-{index}-{digest}")

        added = self.retriever.add_chunks(chunks)
        save = getattr(self.retriever.vector_store, "save", None)
        if save is not None:
            save()
        return added

    def answer(
        self,
        question: str,
        top_k: int = 5,
        history: list[dict] | None = None,
        exclude_sources: set[str] | None = None,
        tenant_id: str = "default",
        as_of: str | None = None,
    ) -> PipelineAnswer:
        # 追问（「那丢了怎么赔？」）本身没有可检索的关键词，检索时把上一轮用户问题并进来；
        # 生成阶段仍然只用原始问题和对话历史，避免模型看到重复内容。
        retrieval_query = build_retrieval_query(question, history)
        contexts = self.retrieve(
            retrieval_query,
            top_k=top_k,
            exclude_sources=exclude_sources,
            tenant_id=tenant_id,
            as_of=as_of,
        )
        # 检索为空或相似度低于阈值都按“资料不足”处理，由接口层引导转人工。
        if not contexts or self.is_below_threshold(contexts):
            return PipelineAnswer(
                answer="当前资料不足，暂时无法给出可靠回答。",
                contexts=[],
            )

        result: GenerationResult = self.generator.generate(
            question,
            self.expand_parent_context(contexts),
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

    def expand_parent_context(
        self,
        contexts: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """命中子块时，把父块文本交给模型，避免答案被切分边界截断。"""
        expanded: list[RetrievedChunk] = []
        for context in contexts:
            parent_text = context.metadata.get("parent_text")
            if not parent_text or parent_text == context.text:
                expanded.append(context)
                continue
            expanded.append(
                RetrievedChunk(
                    text=parent_text,
                    metadata=context.metadata,
                    dense_score=context.dense_score,
                    raw_dense_score=context.raw_dense_score,
                    bm25_score=context.bm25_score,
                    combined_score=context.combined_score,
                    rerank_score=context.rerank_score,
                )
            )
        return expanded

    def retrieve(
        self,
        question: str,
        top_k: int = 5,
        exclude_sources: set[str] | None = None,
        tenant_id: str = "default",
        as_of: str | None = None,
    ) -> list[RetrievedChunk]:
        contexts = self.retriever.search(
            question,
            top_k=top_k,
            exclude_sources=exclude_sources,
            tenant_id=tenant_id,
            as_of=as_of,
        )
        return contexts

    def chunk_count(self) -> int:
        return self.retriever.count()

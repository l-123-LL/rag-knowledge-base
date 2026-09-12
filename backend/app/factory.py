import os
from pathlib import Path

from .embeddings import SentenceTransformerEmbedder
from .generation import DeepSeekGenerator
from .pipeline import RAGPipeline
from .reranker import BGEReranker
from .vector_store import FAISSVectorStore


def build_pipeline() -> RAGPipeline:
    """创建真实 RAG 管线；模型在首次查询时才加载。"""
    embedder = SentenceTransformerEmbedder()
    vector_store = FAISSVectorStore(
        dimensions=1024,
        persist_dir=Path("data/faiss"),
    )
    rerank_model = os.getenv("RERANK_MODEL")
    reranker = BGEReranker(rerank_model) if rerank_model else None
    generator = DeepSeekGenerator()
    return RAGPipeline(
        embedder,
        generator,
        vector_store=vector_store,
        reranker=reranker,
    )

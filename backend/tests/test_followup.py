"""追问指代的测试：什么情况下该把上一轮问题并进检索词。"""

from app.followup import build_retrieval_query, looks_like_followup
from app.generation import GenerationResult, Generator
from app.pipeline import RAGPipeline
from app.retrieval import RetrievedChunk


class HashEmbedderLike:
    """极简确定性向量：只保证同字符更多则更相似，够用即可。"""

    def __init__(self, dimensions: int = 32) -> None:
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for char in text:
                vector[ord(char) % self.dimensions] += 1.0
            vectors.append(vector)
        return vectors


class ContextCapturingGenerator(Generator):
    """把拿到的上下文记下来，方便断言"检索到底用了什么词"。"""

    def __init__(self) -> None:
        self.queries: list[str] = []
        self.contexts: list[RetrievedChunk] = []

    def generate(
        self,
        question: str,
        contexts: list[RetrievedChunk],
        history: list[dict] | None = None,
    ) -> GenerationResult:
        self.contexts = contexts
        self.queries.append(question)
        return GenerationResult(text="ok", prompt_tokens=1, completion_tokens=1, total_tokens=2)


def test_short_question_is_treated_as_followup() -> None:
    assert looks_like_followup("要多久？")
    assert looks_like_followup("那丢了怎么赔？") is True
    assert looks_like_followup("它需要保价吗")


def test_standalone_question_is_not_followup() -> None:
    assert not looks_like_followup("快递签收的时候可以先验收吗？")
    assert not looks_like_followup("")


def test_build_query_merges_previous_user_question() -> None:
    history = [
        {"role": "user", "content": "贵重物品要保价吗？"},
        {"role": "assistant", "content": "要的。"},
    ]

    assert build_retrieval_query("那丢了怎么赔？", history).startswith("贵重物品要保价吗？")


def test_build_query_keeps_standalone_question() -> None:
    history = [{"role": "user", "content": "贵重物品要保价吗？"}]

    assert (
        build_retrieval_query("快递丢了怎么赔偿？", history) == "快递丢了怎么赔偿？"
    )


def test_build_query_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("RAG_FOLLOWUP_MERGING", "false")
    history = [{"role": "user", "content": "贵重物品要保价吗？"}]

    assert build_retrieval_query("那丢了怎么赔？", history) == "那丢了怎么赔？"


def test_pipeline_uses_merged_query_for_retrieval_only() -> None:
    generator = ContextCapturingGenerator()
    pipeline = RAGPipeline(HashEmbedderLike(), generator)
    pipeline.ingest_text(
        "贵重物品可以保价，快件丢失时按保价规则赔偿。",
        metadata={"source": "快递条例"},
    )
    pipeline.ingest_text(
        "会员积分可以在结算时抵扣。",
        metadata={"source": "会员说明"},
    )
    history = [
        {"role": "user", "content": "贵重物品要保价吗？"},
        {"role": "assistant", "content": "要的。"},
    ]

    pipeline.answer("那丢了怎么赔？", history=history, top_k=1)

    # 生成器拿到的仍然是原始问题（历史里已有上下文，不重复喂）
    assert generator.queries == ["那丢了怎么赔？"]
    # 检索命中的是保价/赔偿那条，而不是被短问句带偏
    assert generator.contexts[0].metadata["source"] == "快递条例"

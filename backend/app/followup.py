"""追问指代：把上一轮用户问题并进检索词。

为什么需要：多轮里用户会说「那丢了怎么赔？」「这个要多久？」——这些话本身
没有可检索的关键词。生成阶段我们本来就把对话历史交给了模型，但**检索阶段**
只用当前这句，于是拿回来一堆不相干的片段，模型再聪明也答不上来。

做法很轻：只在「看起来像追问」的时候，把上一轮用户问题拼到检索词前面。
判断标准保守（问句很短、或者以指代词开头），宁可不合并也不要污染检索。
"""

import os

# 指代/转折开头：出现这些词通常说明这句话依赖上文
FOLLOWUP_PREFIXES = (
    "那",
    "这个",
    "那个",
    "它",
    "他",
    "还有",
    "同样",
    "上述",
    "刚才",
    "上面",
    "呢",
)

# 短于这个长度的问题大概率是追问（例如「要多久？」「赔多少？」）。
# 阈值定在 8：中文里 8 字以内往往缺主语或指代对象，而「快递丢了怎么赔偿？」
# 这种 9 字的完整问句不该被当成追问——否则会被上一轮的话题带偏。
FOLLOWUP_MAX_LENGTH = 8


def followup_merging_enabled() -> bool:
    """可用 `RAG_FOLLOWUP_MERGING=false` 关闭（默认开启）。"""
    return os.getenv("RAG_FOLLOWUP_MERGING", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def looks_like_followup(question: str) -> bool:
    stripped = (question or "").strip()
    if not stripped:
        return False
    if len(stripped) <= FOLLOWUP_MAX_LENGTH:
        return True
    return stripped.startswith(FOLLOWUP_PREFIXES)


def build_retrieval_query(question: str, history: list[dict] | None) -> str:
    """追问时返回「上一轮问题 + 本轮问题」，否则原样返回。"""
    if not followup_merging_enabled() or not history:
        return question
    if not looks_like_followup(question):
        return question

    previous = next(
        (
            str(message.get("content", "")).strip()
            for message in reversed(history)
            if message.get("role") == "user" and message.get("content")
        ),
        "",
    )
    if not previous:
        return question
    return f"{previous} {question.strip()}"

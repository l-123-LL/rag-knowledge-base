"""识别「模型在说答不了」，好给它补上转人工出口。

为什么需要：拒答其实有三条路——检索为空、相似度低于阈值、模型看了资料后自己说
「资料里没有这条」。前两条已经会建单转人工，第三条以前没有出口：用户拿到一句
「无法确认」就没了下文，体验上等于卡死。

实现上只做保守的关键词判断，宁可多转一次人工，也不要让用户卡住。
"""

import os

DEFAULT_REFUSAL_MARKERS = (
    "资料不足",
    "无法确认",
    "无法回答",
    "无法提供",
    "没有相关信息",
    "暂无相关",
    "未涉及",
    "资料中未",
)


def refusal_markers() -> tuple[str, ...]:
    """可用 `RAG_REFUSAL_MARKERS` 覆盖（逗号分隔）；写 none/off/0 关闭这层兜底。"""
    raw = os.getenv("RAG_REFUSAL_MARKERS")
    if raw is None or not raw.strip():
        return DEFAULT_REFUSAL_MARKERS
    if raw.strip().lower() in {"none", "off", "0"}:
        return ()
    return tuple(marker.strip() for marker in raw.split(",") if marker.strip())


def looks_like_refusal(answer: str) -> bool:
    """答案看起来像拒答就返回 True（空答案也算）。"""
    if not answer or not answer.strip():
        return True
    text = answer.strip().lower()
    return any(marker.lower() in text for marker in refusal_markers())

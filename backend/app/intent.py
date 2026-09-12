from dataclasses import dataclass


@dataclass
class IntentResult:
    intent: str
    message: str | None = None


def classify_intent(question: str) -> IntentResult:
    """先用规则识别高优先级客服意图，后续可替换为开源意图模型。"""
    normalized = question.lower().replace(" ", "")

    if "投诉" in normalized:
        return IntentResult(
            intent="complaint",
            message="非常抱歉给您带来不便，已为您登记投诉，并转交人工客服处理。",
        )

    if any(
        keyword in normalized
        for keyword in ("人工客服", "转人工", "人工服务", "客服电话")
    ):
        return IntentResult(
            intent="human",
            message="已为您转接人工客服，请稍候。",
        )

    return IntentResult(intent="knowledge")

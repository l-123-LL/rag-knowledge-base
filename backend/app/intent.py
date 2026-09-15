from dataclasses import dataclass


@dataclass
class IntentResult:
    intent: str
    message: str | None = None


# 明确要求转人工的说法。刻意不收「人工客服」这类描述性说法，
# 让「怎么联系人工客服？」继续走 FAQ，能拿到服务时间等完整信息。
HUMAN_KEYWORDS = ("转人工", "转接人工", "人工服务", "人工坐席", "找人工", "客服电话")

# 用户明确表示不需要人工时，不能因为出现关键字就强行转接。
NEGATION_KEYWORDS = (
    "不想转人工",
    "不用转人工",
    "不需要转人工",
    "不要转人工",
    "无需转人工",
    "不想找人工",
    "不用找人工",
    "不需要人工",
)

COMPLAINT_NEGATIONS = ("不想投诉", "不用投诉", "不需要投诉")


def classify_intent(question: str) -> IntentResult:
    """先用规则识别高优先级客服意图，命中后跳过检索与生成，后续可替换为意图模型。"""
    normalized = question.lower().replace(" ", "")
    negated = any(keyword in normalized for keyword in NEGATION_KEYWORDS)

    if "投诉" in normalized and not any(
        keyword in normalized for keyword in COMPLAINT_NEGATIONS
    ):
        return IntentResult(
            intent="complaint",
            message="非常抱歉给您带来不便，已为您登记投诉，并转交人工客服处理。",
        )

    if not negated and any(keyword in normalized for keyword in HUMAN_KEYWORDS):
        return IntentResult(
            intent="human",
            message="已为您转接人工客服，请稍候。",
        )

    return IntentResult(intent="knowledge")

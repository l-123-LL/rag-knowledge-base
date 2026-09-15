from app.intent import classify_intent


def test_explicit_transfer_request_is_human_intent() -> None:
    result = classify_intent("请帮我转人工客服")

    assert result.intent == "human"
    assert result.message is not None


def test_negated_transfer_request_stays_knowledge() -> None:
    # 出现「转人工」但用户明确表示不需要时，不能强行转接。
    assert classify_intent("我不想转人工，能自己处理吗").intent == "knowledge"


def test_complaint_intent_takes_priority_over_faq_keywords() -> None:
    # 句子里同时有「客服」，但投诉意图必须优先命中。
    assert classify_intent("我要投诉你们的客服").intent == "complaint"


def test_informational_agent_question_falls_through_to_knowledge() -> None:
    # 「怎么联系人工客服」应走 FAQ 拿服务时间，而不是被规则直接拦成转接。
    assert classify_intent("怎么联系人工客服？").intent == "knowledge"


def test_general_question_is_knowledge_intent() -> None:
    assert classify_intent("退货要几天").intent == "knowledge"

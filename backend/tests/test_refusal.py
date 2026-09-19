"""模型拒答识别的测试（决定要不要补转人工出口）。"""

from app.refusal import looks_like_refusal


def test_detects_common_refusal_phrases() -> None:
    assert looks_like_refusal("根据现有资料，无法确认定制商品是否可以无理由退货。")
    assert looks_like_refusal("当前资料不足，暂时无法回答。")
    assert looks_like_refusal("提供的资料中未涉及该条款。")
    assert looks_like_refusal("")


def test_normal_answer_is_not_refusal() -> None:
    assert not looks_like_refusal(
        "根据《快递暂行条例》第二十五条，收件人或者代收人有权当面验收。"
    )
    assert not looks_like_refusal("退款会在 3-5 个工作日原路退回，请注意查收。")


def test_markers_can_be_overridden(monkeypatch) -> None:
    # 自定义列表：只认「答不了」，那么"无法确认"这种就不算拒答
    monkeypatch.setenv("RAG_REFUSAL_MARKERS", "答不了")

    assert looks_like_refusal("这个问题我答不了。")
    assert not looks_like_refusal("根据现有资料，无法确认。")


def test_markers_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("RAG_REFUSAL_MARKERS", "none")

    assert not looks_like_refusal("当前资料不足，暂时无法回答。")

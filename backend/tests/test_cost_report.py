"""成本报告的聚合口径测试（不联网、不调模型）。"""

from evaluation.cost_report import summarize

EVENTS = [
    # 调用大模型的一次
    {"route": "rag", "usage": {"prompt_tokens": 880, "completion_tokens": 94}},
    # 零成本路由：FAQ / 规则 / 本地工具，没有 usage
    {"route": "faq"},
    {"route": "intent"},
    {"route": "tools"},
]


def test_costs_average_over_llm_calls_only() -> None:
    result = summarize(EVENTS, input_price_per_million=0.15, output_price_per_million=0.6)

    # 880*0.15/1e6 + 94*0.6/1e6 = 0.000132 + 0.0000564 = 0.0001884
    assert result["total_calls"] == 4
    assert result["llm_calls"] == 1
    assert result["total_tokens"] == 974
    assert result["total_cost_usd"] == 0.000188
    assert result["cost_per_llm_call_usd"] == 0.000188
    assert result["cost_per_1000_llm_calls_usd"] == 0.1884


def test_zero_price_means_zero_cost_but_tokens_still_counted() -> None:
    result = summarize(EVENTS, input_price_per_million=0, output_price_per_million=0)

    assert result["total_cost_usd"] == 0.0
    assert result["total_tokens"] == 974


def test_empty_log_is_safe() -> None:
    result = summarize([], input_price_per_million=0.15, output_price_per_million=0.6)

    assert result["total_calls"] == 0
    assert result["llm_calls"] == 0
    assert result["cost_per_llm_call_usd"] is None

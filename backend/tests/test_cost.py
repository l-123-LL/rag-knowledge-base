from app.cost import calculate_cost


def test_calculate_cost_returns_none_when_prices_missing() -> None:
    assert calculate_cost({"total_tokens": 100}) is None


def test_calculate_cost_uses_token_usage() -> None:
    cost = calculate_cost(
        {"prompt_tokens": 1000, "completion_tokens": 500},
        input_price_per_million=1.0,
        output_price_per_million=2.0,
    )

    assert cost == 0.002

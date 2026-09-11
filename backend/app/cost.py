def calculate_cost(
    usage: dict[str, int] | None,
    input_price_per_million: float = 0.0,
    output_price_per_million: float = 0.0,
) -> float | None:
    """按每百万 token 价格估算单次成本；价格未配置时返回 None。"""
    if not usage:
        return None

    if input_price_per_million <= 0 and output_price_per_million <= 0:
        return None

    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    return (
        prompt_tokens / 1_000_000 * input_price_per_million
        + completion_tokens / 1_000_000 * output_price_per_million
    )

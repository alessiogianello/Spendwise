"""USD price per token, by model. Source: Anthropic pricing table (cached 2026-06-24).
Cache writes are billed ~1.25x input price, cache reads ~0.1x input price."""

PRICING_PER_1M = {
    "claude-fable-5-1": {"input": 10.00, "output": 50.00},
    "claude-fable-5": {"input": 10.00, "output": 50.00},
    "claude-opus-5": {"input": 5.00, "output": 25.00},
    "claude-opus-4-8": {"input": 5.00, "output": 25.00},
    "claude-opus-4-7": {"input": 5.00, "output": 25.00},
    "claude-opus-4-6": {"input": 5.00, "output": 25.00},
    "claude-sonnet-5": {"input": 2.00, "output": 10.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}


def estimate_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float:
    rates = PRICING_PER_1M.get(model)
    if rates is None:
        return 0.0
    cost = (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
        + cache_creation_tokens * rates["input"] * 1.25
        + cache_read_tokens * rates["input"] * 0.1
    ) / 1_000_000
    return round(cost, 6)

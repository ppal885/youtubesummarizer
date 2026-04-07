from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TokenUsageMetrics:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_estimate_usd: float


def estimate_token_count(text: str | None) -> int:
    if not text:
        return 0
    normalized = " ".join(str(text).split())
    if not normalized:
        return 0
    return max(1, math.ceil(len(normalized) / 4))


def extract_openai_token_usage(usage: Any) -> tuple[int | None, int | None, int | None]:
    if usage is None:
        return None, None, None
    return (
        _safe_int(getattr(usage, "prompt_tokens", None)),
        _safe_int(getattr(usage, "completion_tokens", None)),
        _safe_int(getattr(usage, "total_tokens", None)),
    )


def extract_anthropic_token_usage(usage: Any) -> tuple[int | None, int | None, int | None]:
    if usage is None:
        return None, None, None
    input_tokens = _safe_int(getattr(usage, "input_tokens", None))
    output_tokens = _safe_int(getattr(usage, "output_tokens", None))
    total_tokens = None
    if input_tokens is not None or output_tokens is not None:
        total_tokens = (input_tokens or 0) + (output_tokens or 0)
    return input_tokens, output_tokens, total_tokens


def build_token_usage_metrics(
    *,
    provider: str,
    model: str,
    input_text: str | None,
    output_text: str | None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
) -> TokenUsageMetrics:
    normalized_input = _normalize_non_negative(input_tokens)
    normalized_output = _normalize_non_negative(output_tokens)
    estimated_input = estimate_token_count(input_text)
    estimated_output = estimate_token_count(output_text)

    effective_input = normalized_input if normalized_input is not None else estimated_input
    effective_output = normalized_output if normalized_output is not None else estimated_output
    effective_total = _normalize_non_negative(total_tokens)
    if effective_total is None:
        effective_total = effective_input + effective_output
    else:
        effective_total = max(effective_total, effective_input + effective_output)

    return TokenUsageMetrics(
        input_tokens=effective_input,
        output_tokens=effective_output,
        total_tokens=effective_total,
        cost_estimate_usd=estimate_cost_usd(provider, model, effective_input, effective_output),
    )


def estimate_cost_usd(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    in_rate, out_rate = _pricing_for(provider, model)
    return round((input_tokens * in_rate) + (output_tokens * out_rate), 6)


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_non_negative(value: int | None) -> int | None:
    if value is None:
        return None
    return max(0, int(value))


def _pricing_for(provider: str, model: str) -> tuple[float, float]:
    provider_l = provider.lower()
    model_l = model.lower()

    if provider_l == "mock":
        return 0.0, 0.0

    known_prices_per_token: list[tuple[tuple[str, ...], float, float]] = [
        (("gpt-4o-mini",), 0.00000015, 0.0000006),
        (("gpt-4o",), 0.000005, 0.000015),
        (("claude-3-5-haiku", "claude-3-haiku"), 0.0000008, 0.000004),
        (("claude-3-5-sonnet", "claude-3-7-sonnet", "claude-sonnet"), 0.000003, 0.000015),
    ]

    for prefixes, input_rate, output_rate in known_prices_per_token:
        if any(prefix in model_l for prefix in prefixes):
            return input_rate, output_rate

    return 0.0, 0.0

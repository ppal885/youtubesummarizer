from app.observability.llm_request_usage import llm_request_usage_context, record_llm_usage
from app.services.llm.token_usage import TokenUsageMetrics, build_token_usage_metrics, estimate_token_count


def test_estimate_token_count_uses_simple_text_heuristic() -> None:
    assert estimate_token_count("") == 0
    assert estimate_token_count("abcd") == 1
    assert estimate_token_count("abcdefgh") == 2
    assert estimate_token_count("hello   world") >= 2


def test_build_token_usage_metrics_falls_back_to_estimation_and_costs() -> None:
    metrics = build_token_usage_metrics(
        provider="openai-compatible",
        model="gpt-4o-mini",
        input_text="abcdefgh",
        output_text="abcd",
    )

    assert metrics.input_tokens == 2
    assert metrics.output_tokens == 1
    assert metrics.total_tokens == 3
    assert metrics.cost_estimate_usd > 0


def test_llm_request_usage_context_aggregates_and_persists(monkeypatch) -> None:
    per_call_logs: list[dict] = []
    request_logs: list[dict] = []
    persisted_rows: list[dict] = []

    monkeypatch.setattr(
        "app.observability.llm_request_usage.log_llm_token_usage",
        lambda **kwargs: per_call_logs.append(kwargs),
    )
    monkeypatch.setattr(
        "app.observability.llm_request_usage.log_llm_request_usage",
        lambda **kwargs: request_logs.append(kwargs),
    )
    monkeypatch.setattr(
        "app.observability.llm_request_usage._persist_request_usage",
        lambda state: persisted_rows.append(
            {
                "endpoint": state.endpoint,
                "video_id": state.video_id,
                "input_tokens": state.input_tokens,
                "output_tokens": state.output_tokens,
                "total_tokens": state.total_tokens,
                "llm_call_count": state.llm_call_count,
                "cost_estimate_usd": state.cost_estimate_usd,
            }
        ),
    )

    with llm_request_usage_context(endpoint="notes", video_id="abc123"):
        record_llm_usage(
            provider="openai-compatible",
            model="gpt-4o-mini",
            capability="generate_study_notes",
            metrics=TokenUsageMetrics(
                input_tokens=10,
                output_tokens=4,
                total_tokens=14,
                cost_estimate_usd=0.001,
            ),
        )
        record_llm_usage(
            provider="openai-compatible",
            model="gpt-4o-mini",
            capability="generate_study_notes",
            metrics=TokenUsageMetrics(
                input_tokens=6,
                output_tokens=2,
                total_tokens=8,
                cost_estimate_usd=0.0004,
            ),
        )

    assert len(per_call_logs) == 2
    assert len(request_logs) == 1
    assert len(persisted_rows) == 1
    assert persisted_rows[0]["endpoint"] == "notes"
    assert persisted_rows[0]["video_id"] == "abc123"
    assert persisted_rows[0]["input_tokens"] == 16
    assert persisted_rows[0]["output_tokens"] == 6
    assert persisted_rows[0]["total_tokens"] == 22
    assert persisted_rows[0]["llm_call_count"] == 2

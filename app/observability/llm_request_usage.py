from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator

from app.observability.llm_calls import log_llm_request_usage, log_llm_token_usage
from app.observability.request_context import get_trace_id
from app.services.llm.token_usage import TokenUsageMetrics

_LOG = logging.getLogger(__name__)
_CURRENT_USAGE: ContextVar["_RequestUsageState | None"] = ContextVar(
    "youtube_summarizer_llm_request_usage",
    default=None,
)


@dataclass
class _RequestUsageState:
    endpoint: str | None
    video_id: str | None
    trace_id: str | None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_estimate_usd: float = 0.0
    llm_call_count: int = 0


@contextmanager
def llm_request_usage_context(
    *,
    endpoint: str | None = None,
    video_id: str | None = None,
) -> Iterator[None]:
    existing = _CURRENT_USAGE.get()
    if existing is not None:
        if existing.endpoint is None and endpoint:
            existing.endpoint = endpoint
        if existing.video_id is None and video_id:
            existing.video_id = video_id
        yield
        return

    state = _RequestUsageState(
        endpoint=endpoint,
        video_id=video_id,
        trace_id=get_trace_id(),
    )
    previous = _CURRENT_USAGE.get()
    token = _CURRENT_USAGE.set(state)
    try:
        yield
    finally:
        try:
            if state.llm_call_count > 0:
                log_llm_request_usage(
                    trace_id=state.trace_id,
                    endpoint=state.endpoint or "unknown",
                    video_id=state.video_id,
                    input_tokens=state.input_tokens,
                    output_tokens=state.output_tokens,
                    total_tokens=state.total_tokens,
                    llm_call_count=state.llm_call_count,
                    cost_estimate_usd=state.cost_estimate_usd,
                )
                _persist_request_usage(state)
        finally:
            try:
                _CURRENT_USAGE.reset(token)
            except ValueError:
                _CURRENT_USAGE.set(previous)


def record_llm_usage(
    *,
    provider: str,
    model: str,
    capability: str,
    metrics: TokenUsageMetrics,
) -> None:
    log_llm_token_usage(
        provider=provider,
        model=model,
        capability=capability,
        input_tokens=metrics.input_tokens,
        output_tokens=metrics.output_tokens,
        total_tokens=metrics.total_tokens,
        cost_estimate_usd=metrics.cost_estimate_usd,
    )

    current = _CURRENT_USAGE.get()
    if current is None:
        return
    current.input_tokens += metrics.input_tokens
    current.output_tokens += metrics.output_tokens
    current.total_tokens += metrics.total_tokens
    current.cost_estimate_usd = round(current.cost_estimate_usd + metrics.cost_estimate_usd, 6)
    current.llm_call_count += 1


def _persist_request_usage(state: _RequestUsageState) -> None:
    try:
        from app.db.session import SessionLocal
        from app.repositories.llm_usage_repository import LLMUsageRepository

        with SessionLocal() as db:
            LLMUsageRepository().save(
                db,
                trace_id=state.trace_id,
                video_id=state.video_id,
                endpoint=state.endpoint or "unknown",
                input_tokens=state.input_tokens,
                output_tokens=state.output_tokens,
                total_tokens=state.total_tokens,
                llm_call_count=state.llm_call_count,
                cost_estimate_usd=state.cost_estimate_usd,
            )
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("Could not persist LLM request usage metrics: %s", exc)

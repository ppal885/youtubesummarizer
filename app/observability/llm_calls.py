"""Structured logs for every provider invocation."""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from datetime import datetime, timezone
from typing import Any, TypeVar

from app.observability.request_context import get_trace_id

_LOGGER_NAME = "youtube_summarizer.llm.calls"
_CONFIGURED = False
_SAFE_DETAIL = re.compile(r"[\x00-\x1f]")

T = TypeVar("T")


def configure_llm_call_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    log = logging.getLogger(_LOGGER_NAME)
    log.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
    log.propagate = False
    _CONFIGURED = True


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        return _SAFE_DETAIL.sub(" ", value)[:500]
    return value


def log_llm_call(
    *,
    provider: str,
    model: str,
    capability: str,
    success: bool,
    elapsed_ms: float,
    trace_id: str | None = None,
    error_type: str | None = None,
    detail: str | None = None,
) -> None:
    configure_llm_call_logging()
    payload: dict[str, Any] = {
        "ts": _now_iso(),
        "component": "llm",
        "provider": provider,
        "model": model,
        "capability": capability,
        "success": success,
        "elapsed_ms": round(elapsed_ms, 2),
    }
    effective_trace_id = trace_id if trace_id is not None else get_trace_id()
    if effective_trace_id:
        payload["trace_id"] = effective_trace_id
    if error_type:
        payload["error_type"] = error_type
    if detail:
        payload["detail"] = _scrub(detail)
    logging.getLogger(_LOGGER_NAME).info(json.dumps(payload, ensure_ascii=False, default=str))


def log_llm_invalid_output(
    *,
    provider: str,
    model: str,
    capability: str,
    attempt: int,
    detail: str,
    raw_output: str | None = None,
    fallback_used: bool = False,
    trace_id: str | None = None,
) -> None:
    configure_llm_call_logging()
    payload: dict[str, Any] = {
        "ts": _now_iso(),
        "component": "llm_validation",
        "provider": provider,
        "model": model,
        "capability": capability,
        "attempt": attempt,
        "fallback_used": fallback_used,
        "detail": _scrub(detail),
    }
    effective_trace_id = trace_id if trace_id is not None else get_trace_id()
    if effective_trace_id:
        payload["trace_id"] = effective_trace_id
    if raw_output is not None:
        payload["raw_output_excerpt"] = _scrub(raw_output)
    logging.getLogger(_LOGGER_NAME).info(json.dumps(payload, ensure_ascii=False, default=str))


def log_llm_retry(
    *,
    provider: str,
    model: str,
    capability: str,
    retry_number: int,
    delay_ms: float,
    detail: str,
    error_type: str | None = None,
    trace_id: str | None = None,
) -> None:
    configure_llm_call_logging()
    payload: dict[str, Any] = {
        "ts": _now_iso(),
        "component": "llm_retry",
        "provider": provider,
        "model": model,
        "capability": capability,
        "retry_number": retry_number,
        "delay_ms": round(delay_ms, 2),
        "detail": _scrub(detail),
    }
    effective_trace_id = trace_id if trace_id is not None else get_trace_id()
    if effective_trace_id:
        payload["trace_id"] = effective_trace_id
    if error_type:
        payload["error_type"] = error_type
    logging.getLogger(_LOGGER_NAME).info(json.dumps(payload, ensure_ascii=False, default=str))


def log_llm_fallback(
    *,
    capability: str,
    from_provider: str,
    from_model: str,
    to_provider: str,
    to_model: str,
    detail: str,
    trace_id: str | None = None,
) -> None:
    configure_llm_call_logging()
    payload: dict[str, Any] = {
        "ts": _now_iso(),
        "component": "llm_fallback",
        "capability": capability,
        "from_provider": from_provider,
        "from_model": from_model,
        "to_provider": to_provider,
        "to_model": to_model,
        "detail": _scrub(detail),
    }
    effective_trace_id = trace_id if trace_id is not None else get_trace_id()
    if effective_trace_id:
        payload["trace_id"] = effective_trace_id
    logging.getLogger(_LOGGER_NAME).info(json.dumps(payload, ensure_ascii=False, default=str))


def log_llm_safe_default(
    *,
    provider: str,
    model: str,
    capability: str,
    detail: str,
    error_type: str | None = None,
    trace_id: str | None = None,
) -> None:
    configure_llm_call_logging()
    payload: dict[str, Any] = {
        "ts": _now_iso(),
        "component": "llm_safe_default",
        "provider": provider,
        "model": model,
        "capability": capability,
        "detail": _scrub(detail),
    }
    effective_trace_id = trace_id if trace_id is not None else get_trace_id()
    if effective_trace_id:
        payload["trace_id"] = effective_trace_id
    if error_type:
        payload["error_type"] = error_type
    logging.getLogger(_LOGGER_NAME).info(json.dumps(payload, ensure_ascii=False, default=str))


def log_llm_token_usage(
    *,
    provider: str,
    model: str,
    capability: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    cost_estimate_usd: float,
    trace_id: str | None = None,
) -> None:
    configure_llm_call_logging()
    payload: dict[str, Any] = {
        "ts": _now_iso(),
        "component": "llm_usage_call",
        "provider": provider,
        "model": model,
        "capability": capability,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_estimate_usd": round(cost_estimate_usd, 6),
    }
    effective_trace_id = trace_id if trace_id is not None else get_trace_id()
    if effective_trace_id:
        payload["trace_id"] = effective_trace_id
    logging.getLogger(_LOGGER_NAME).info(json.dumps(payload, ensure_ascii=False, default=str))


def log_llm_request_usage(
    *,
    endpoint: str,
    video_id: str | None,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    llm_call_count: int,
    cost_estimate_usd: float,
    trace_id: str | None = None,
) -> None:
    configure_llm_call_logging()
    payload: dict[str, Any] = {
        "ts": _now_iso(),
        "component": "llm_usage_request",
        "endpoint": endpoint,
        "video_id": video_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "llm_call_count": llm_call_count,
        "cost_estimate_usd": round(cost_estimate_usd, 6),
    }
    effective_trace_id = trace_id if trace_id is not None else get_trace_id()
    if effective_trace_id:
        payload["trace_id"] = effective_trace_id
    logging.getLogger(_LOGGER_NAME).info(json.dumps(payload, ensure_ascii=False, default=str))


def log_llm_cache_event(
    *,
    provider: str,
    model: str,
    capability: str,
    cache_key: str,
    hit: bool,
    trace_id: str | None = None,
) -> None:
    configure_llm_call_logging()
    payload: dict[str, Any] = {
        "ts": _now_iso(),
        "component": "llm_cache",
        "provider": provider,
        "model": model,
        "capability": capability,
        "hit": hit,
        "cache_key_prefix": cache_key[:12],
    }
    effective_trace_id = trace_id if trace_id is not None else get_trace_id()
    if effective_trace_id:
        payload["trace_id"] = effective_trace_id
    logging.getLogger(_LOGGER_NAME).info(json.dumps(payload, ensure_ascii=False, default=str))


def run_logged_call(
    *,
    provider: str,
    model: str,
    capability: str,
    fn: Callable[[], T],
) -> T:
    trace_id = get_trace_id()
    t0 = time.perf_counter()
    try:
        result = fn()
    except Exception as exc:  # noqa: BLE001
        log_llm_call(
            provider=provider,
            model=model,
            capability=capability,
            success=False,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            trace_id=trace_id,
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        raise
    log_llm_call(
        provider=provider,
        model=model,
        capability=capability,
        success=True,
        elapsed_ms=(time.perf_counter() - t0) * 1000,
        trace_id=trace_id,
    )
    return result


async def run_logged_call_async(
    *,
    provider: str,
    model: str,
    capability: str,
    fn: Callable[[], Awaitable[T]],
) -> T:
    trace_id = get_trace_id()
    t0 = time.perf_counter()
    try:
        result = await fn()
    except Exception as exc:  # noqa: BLE001
        log_llm_call(
            provider=provider,
            model=model,
            capability=capability,
            success=False,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            trace_id=trace_id,
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        raise
    log_llm_call(
        provider=provider,
        model=model,
        capability=capability,
        success=True,
        elapsed_ms=(time.perf_counter() - t0) * 1000,
        trace_id=trace_id,
    )
    return result


def iter_logged_call(
    *,
    provider: str,
    model: str,
    capability: str,
    factory: Callable[[], Iterator[str]],
) -> Iterator[str]:
    trace_id = get_trace_id()
    t0 = time.perf_counter()
    try:
        iterator = factory()
    except Exception as exc:  # noqa: BLE001
        log_llm_call(
            provider=provider,
            model=model,
            capability=capability,
            success=False,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            trace_id=trace_id,
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        raise

    def _gen() -> Iterator[str]:
        try:
            for item in iterator:
                yield item
        except Exception as exc:  # noqa: BLE001
            log_llm_call(
                provider=provider,
                model=model,
                capability=capability,
                success=False,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                trace_id=trace_id,
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            raise
        log_llm_call(
            provider=provider,
            model=model,
            capability=capability,
            success=True,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            trace_id=trace_id,
        )

    return _gen()


async def aiter_logged_call(
    *,
    provider: str,
    model: str,
    capability: str,
    factory: Callable[[], AsyncIterator[str]],
) -> AsyncIterator[str]:
    trace_id = get_trace_id()
    t0 = time.perf_counter()
    try:
        iterator = factory()
    except Exception as exc:  # noqa: BLE001
        log_llm_call(
            provider=provider,
            model=model,
            capability=capability,
            success=False,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            trace_id=trace_id,
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        raise
    try:
        async for item in iterator:
            yield item
    except Exception as exc:  # noqa: BLE001
        log_llm_call(
            provider=provider,
            model=model,
            capability=capability,
            success=False,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            trace_id=trace_id,
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        raise
    log_llm_call(
        provider=provider,
        model=model,
        capability=capability,
        success=True,
        elapsed_ms=(time.perf_counter() - t0) * 1000,
        trace_id=trace_id,
    )

"""HTTP request tracing: request_id, per-stage durations, total latency (structured JSON logs).

**Middleware** (``RequestTracingMiddleware``): assigns ``X-Request-ID`` (or honors inbound
``X-Request-ID`` / ``X-Correlation-ID``), binds ``RequestTrace`` for the request, sets
``trace_context`` to the same id, and logs:

- ``http.request.start`` — ``request_id``, ``method``, ``path``, ``client_ip``, ``start_ts``
- ``http.request.complete`` — ``request_id``, ``status_code``, ``total_duration_ms``,
  ``stages`` (``[{name, duration_ms}, ...]``), ``stage_count``, optional ``error_type`` / ``error_detail``

For ``StreamingResponse``, ``complete`` is emitted after the body finishes so ``total_duration_ms``
includes the full SSE/stream lifetime.

**Stages**: wrap work with ``with request_trace_stage("my.stage"):``; durations appear in
``http.request.complete`` ``stages``.

**Downstream logs**: ``log_summarize_line`` / ``log_ask_line`` add ``request_id`` when an HTTP
trace is active.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator

_LOGGER_NAME = "youtube_summarizer.request.trace"
_CONFIGURED = False
_SAFE = re.compile(r"[\x00-\x1f]")
_MAX_PATH = 512
_MAX_INCOMING_REQUEST_ID_LEN = 128


@dataclass
class RequestTrace:
    """Mutable trace state for the active HTTP request (set by middleware)."""

    request_id: str
    start_perf: float
    start_iso: str
    method: str
    path: str
    client_ip: str | None = None
    stages: list[dict[str, Any]] = field(default_factory=list)

    def add_stage(self, name: str, duration_ms: float) -> None:
        self.stages.append(
            {
                "name": _scrub_str(name, 120),
                "duration_ms": round(duration_ms, 2),
            }
        )


_REQUEST_TRACE_CTX: ContextVar[RequestTrace | None] = ContextVar("youtube_summarizer_request_trace", default=None)


def configure_request_tracing_logging() -> None:
    """Stdout JSON lines (same pattern as other observability modules)."""
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


def _scrub_str(value: str, max_len: int) -> str:
    return _SAFE.sub(" ", value)[:max_len]


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        return _scrub_str(value, 500)
    return value


def new_request_id() -> str:
    return str(uuid.uuid4())


def parse_incoming_request_id(header_value: str | None) -> str | None:
    """Return a sanitized client-provided id, or None if absent/invalid."""
    if not header_value or not str(header_value).strip():
        return None
    raw = str(header_value).strip()
    if len(raw) > _MAX_INCOMING_REQUEST_ID_LEN:
        raw = raw[:_MAX_INCOMING_REQUEST_ID_LEN]
    if not re.fullmatch(r"[\w\-:.]+", raw):
        return None
    return raw


def get_request_trace() -> RequestTrace | None:
    return _REQUEST_TRACE_CTX.get()


def bind_request_trace(trace: RequestTrace) -> Token:
    return _REQUEST_TRACE_CTX.set(trace)


def reset_request_trace(token: Token) -> None:
    try:
        _REQUEST_TRACE_CTX.reset(token)
    except ValueError:
        pass


def log_request_trace_event(event: str, **fields: Any) -> None:
    """Emit one JSON object (component ``http``)."""
    configure_request_tracing_logging()
    payload: dict[str, Any] = {
        "ts": _now_iso(),
        "component": "http",
        "event": event,
    }
    for k, v in fields.items():
        if v is None:
            continue
        payload[k] = _scrub(v)
    logging.getLogger(_LOGGER_NAME).info(json.dumps(payload, ensure_ascii=False, default=str))


def log_request_start(trace: RequestTrace) -> None:
    log_request_trace_event(
        "http.request.start",
        request_id=trace.request_id,
        method=trace.method,
        path=trace.path,
        client_ip=trace.client_ip,
        start_ts=trace.start_iso,
    )


def log_request_complete(
    trace: RequestTrace,
    *,
    status_code: int,
    total_duration_ms: float,
    error_type: str | None = None,
    error_detail: str | None = None,
) -> None:
    log_request_trace_event(
        "http.request.complete",
        request_id=trace.request_id,
        method=trace.method,
        path=trace.path,
        status_code=status_code,
        total_duration_ms=round(total_duration_ms, 2),
        stages=trace.stages,
        stage_count=len(trace.stages),
        error_type=error_type,
        error_detail=error_detail,
    )


@contextmanager
def request_trace_stage(name: str) -> Iterator[None]:
    """
    Record wall time for a named stage (appears in ``http.request.complete`` ``stages``).

    No-op when there is no active ``RequestTrace`` (e.g. background jobs).
    """
    trace = get_request_trace()
    if trace is None:
        yield
        return
    t0 = time.perf_counter()
    try:
        yield
    finally:
        trace.add_stage(name, (time.perf_counter() - t0) * 1000)


def build_trace_for_request(
    request_id: str,
    method: str,
    path: str,
    *,
    client_ip: str | None,
) -> RequestTrace:
    return RequestTrace(
        request_id=request_id,
        start_perf=time.perf_counter(),
        start_iso=_now_iso(),
        method=method.upper(),
        path=_scrub_str(path, _MAX_PATH),
        client_ip=client_ip,
    )

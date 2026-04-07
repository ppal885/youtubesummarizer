"""ASGI middleware: request_id, trace context, structured request lifecycle logs."""

from __future__ import annotations

import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability.request_context import trace_context
from app.observability.request_tracing import (
    bind_request_trace,
    build_trace_for_request,
    log_request_complete,
    log_request_start,
    new_request_id,
    parse_incoming_request_id,
    reset_request_trace,
)


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Assign ``X-Request-ID`` (or honor inbound ``X-Request-ID`` / ``X-Correlation-ID``),
    bind ``RequestTrace`` for ``request_trace_stage()``, set default ``trace_context``,
    and emit ``http.request.start`` / ``http.request.complete`` JSON logs.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        rid = parse_incoming_request_id(
            request.headers.get("x-request-id") or request.headers.get("x-correlation-id")
        )
        if rid is None:
            rid = new_request_id()

        trace = build_trace_for_request(
            rid,
            request.method,
            request.url.path,
            client_ip=_client_ip(request),
        )
        token = bind_request_trace(trace)
        log_request_start(trace)
        status_code = 500
        error_type: str | None = None
        error_detail: str | None = None
        response: Response | None = None
        try:
            with trace_context(rid):
                response = await call_next(request)
                status_code = response.status_code
        except Exception as exc:
            error_type = type(exc).__name__
            error_detail = str(exc)[:800]
            raise
        finally:
            total_ms = (time.perf_counter() - trace.start_perf) * 1000
            log_request_complete(
                trace,
                status_code=status_code,
                total_duration_ms=total_ms,
                error_type=error_type,
                error_detail=error_detail,
            )
            reset_request_trace(token)

        assert response is not None
        response.headers["X-Request-ID"] = rid
        return response

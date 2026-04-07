"""In-memory per-client request rate limiting (sliding 60s window)."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client:
        return request.client.host
    return "unknown"


def rate_limit_user_key(request: Request) -> str:
    """
    Stable bucket key: Authorization, then X-API-Key, then client IP (X-Forwarded-For aware).
    """
    auth = request.headers.get("authorization")
    if auth:
        return f"auth:{auth}"
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"key:{api_key}"
    return f"ip:{_client_ip(request)}"


class _SlidingWindowLimiter:
    __slots__ = ("_limit", "_window_seconds", "_buckets", "_lock")

    def __init__(self, requests_per_minute: int, window_seconds: float = 60.0) -> None:
        self._limit = max(1, int(requests_per_minute))
        self._window_seconds = float(window_seconds)
        self._buckets: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self._window_seconds
            dq = self._buckets.setdefault(key, deque())
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= self._limit:
                return False
            dq.append(now)
            return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Return 429 when a user exceeds ``requests_per_minute`` in a sliding 60s window.

    Skips ``OPTIONS`` and paths not under ``path_prefix`` (default ``/api/``).
    Add this middleware **before** ``CORSMiddleware`` so error responses still get CORS headers.
    """

    def __init__(
        self,
        app: Callable,
        *,
        requests_per_minute: int = 60,
        window_seconds: float = 60.0,
        enabled: bool = True,
        path_prefix: str = "/api/",
    ) -> None:
        super().__init__(app)
        self._enabled = enabled
        self._path_prefix = path_prefix
        self._limiter = _SlidingWindowLimiter(requests_per_minute, window_seconds=window_seconds)
        self._retry_after_seconds = max(1, int(window_seconds))

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self._enabled or request.method.upper() == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if not path.startswith(self._path_prefix):
            return await call_next(request)

        key = rate_limit_user_key(request)
        if not await self._limiter.allow(key):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(self._retry_after_seconds)},
            )

        return await call_next(request)

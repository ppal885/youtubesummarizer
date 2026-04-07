"""Request-scoped trace id for logs emitted deep in service/provider layers."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

_TRACE_ID: ContextVar[str | None] = ContextVar("youtube_summarizer_trace_id", default=None)


def get_trace_id() -> str | None:
    return _TRACE_ID.get()


@contextmanager
def trace_context(trace_id: str | None) -> Iterator[None]:
    previous = _TRACE_ID.get()
    token = _TRACE_ID.set(trace_id)
    try:
        yield
    finally:
        try:
            _TRACE_ID.reset(token)
        except ValueError:
            _TRACE_ID.set(previous)

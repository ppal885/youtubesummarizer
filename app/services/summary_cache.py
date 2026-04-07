"""In-memory, thread-safe cache for LLM summary outputs (MVP).

Key: (video_id, summary_type, learning_level, developer_mode). Language is intentionally not part of the key
per product spec; use a different summary_type or clear cache if multi-language per video matters.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CachedSummaryPayload:
    summary: str
    bullets: tuple[str, ...]
    suggested_questions: tuple[str, ...]
    chapters: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    developer_digest: dict[str, Any] | None = None


class SummaryMemoryCache:
    """Thread-safe dict cache for summarization LLM results."""

    __slots__ = ("_lock", "_store")

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._store: dict[tuple[str, str, str, bool], CachedSummaryPayload] = {}

    def get(
        self,
        video_id: str,
        summary_type: str,
        learning_level: str,
        developer_mode: bool,
    ) -> CachedSummaryPayload | None:
        key = (video_id, summary_type, learning_level, developer_mode)
        with self._lock:
            return self._store.get(key)

    def set(
        self,
        video_id: str,
        summary_type: str,
        learning_level: str,
        developer_mode: bool,
        payload: CachedSummaryPayload,
    ) -> None:
        key = (video_id, summary_type, learning_level, developer_mode)
        with self._lock:
            self._store[key] = payload


_default_cache = SummaryMemoryCache()


def get_summary_memory_cache() -> SummaryMemoryCache:
    return _default_cache

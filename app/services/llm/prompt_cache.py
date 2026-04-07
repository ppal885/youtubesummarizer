from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass
from typing import Callable


@dataclass
class PromptCacheEntry:
    value: str
    expires_at: float


class InMemoryPromptCache:
    """Thread-safe in-memory TTL cache for prompt->response mappings."""

    def __init__(
        self,
        *,
        default_ttl_seconds: float = 300.0,
        now_fn: Callable[[], float] | None = None,
    ) -> None:
        self._default_ttl_seconds = max(1.0, float(default_ttl_seconds))
        self._now = now_fn if now_fn is not None else time.time
        self._entries: dict[str, PromptCacheEntry] = {}
        self._lock = threading.RLock()

    def make_key(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def get(self, prompt: str) -> tuple[str | None, str]:
        key = self.make_key(prompt)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None, key
            if entry.expires_at <= self._now():
                self._entries.pop(key, None)
                return None, key
            return entry.value, key

    def set(self, prompt: str, value: str, *, ttl_seconds: float | None = None) -> str:
        key = self.make_key(prompt)
        ttl = self._default_ttl_seconds if ttl_seconds is None else max(1.0, float(ttl_seconds))
        with self._lock:
            self._entries[key] = PromptCacheEntry(
                value=value,
                expires_at=self._now() + ttl,
            )
        return key

    def delete(self, prompt: str) -> None:
        key = self.make_key(prompt)
        with self._lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


_PROMPT_CACHE = InMemoryPromptCache()


def get_prompt_response_cache() -> InMemoryPromptCache:
    return _PROMPT_CACHE

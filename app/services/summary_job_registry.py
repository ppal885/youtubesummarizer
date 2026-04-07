"""Thread-safe in-memory mirror of summarize job status (for observability and fast lookups)."""

from __future__ import annotations

import threading
from typing import Literal

JobStatus = Literal["queued", "running", "completed", "failed"]


class SummaryJobMemoryRegistry:
    """Tracks latest known status per job id; DB remains the source of truth for persisted results."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status: dict[str, JobStatus] = {}

    def set_status(self, job_id: str, status: JobStatus) -> None:
        with self._lock:
            self._status[job_id] = status

    def get_status(self, job_id: str) -> JobStatus | None:
        with self._lock:
            return self._status.get(job_id)

    def forget(self, job_id: str) -> None:
        with self._lock:
            self._status.pop(job_id, None)


_registry = SummaryJobMemoryRegistry()


def get_summary_job_memory_registry() -> SummaryJobMemoryRegistry:
    return _registry

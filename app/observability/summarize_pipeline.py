"""One-line JSON logs for the /summarize pipeline (stdout only)."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

_LOGGER_NAME = "youtube_summarizer.summarize.pipeline"
_CONFIGURED = False

_SAFE_DETAIL = re.compile(r"[\x00-\x1f]")


def configure_summarize_pipeline_logging() -> None:
    """Attach a stdout handler that prints the log message as-is (JSON lines)."""
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


def log_summarize_line(event: str, **fields: Any) -> None:
    """Emit a single JSON object on one line (readable in terminals and log files)."""
    from app.observability.request_tracing import get_request_trace

    configure_summarize_pipeline_logging()
    payload: dict[str, Any] = {
        "ts": _now_iso(),
        "component": "summarize",
        "event": event,
    }
    active = get_request_trace()
    if active is not None and "request_id" not in fields:
        payload["request_id"] = active.request_id
    for k, v in fields.items():
        if v is None:
            continue
        payload[k] = _scrub(v)
    logging.getLogger(_LOGGER_NAME).info(json.dumps(payload, ensure_ascii=False, default=str))


def log_summarize_failure(
    *,
    trace_id: str,
    error_stage: str,
    error_type: str,
    detail: str,
    video_id: str | None = None,
    elapsed_ms: float | None = None,
) -> None:
    log_summarize_line(
        "summarize.pipeline.failed",
        trace_id=trace_id,
        success=False,
        error_stage=error_stage,
        error_type=error_type,
        detail=detail[:800] if detail else "",
        video_id=video_id,
        elapsed_ms=round(elapsed_ms, 2) if elapsed_ms is not None else None,
    )

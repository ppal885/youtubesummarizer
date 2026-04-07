"""Structured logs for the ask workflow."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

_LOGGER_NAME = "youtube_summarizer.ask.pipeline"
_CONFIGURED = False
_SAFE_DETAIL = re.compile(r"[\x00-\x1f]")


def configure_ask_pipeline_logging() -> None:
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


def log_ask_line(event: str, **fields: Any) -> None:
    configure_ask_pipeline_logging()
    payload: dict[str, Any] = {
        "ts": _now_iso(),
        "component": "ask",
        "event": event,
    }
    for key, value in fields.items():
        if value is None:
            continue
        payload[key] = _scrub(value)
    logging.getLogger(_LOGGER_NAME).info(json.dumps(payload, ensure_ascii=False, default=str))

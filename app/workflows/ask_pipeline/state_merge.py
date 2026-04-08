"""Merge LangGraph-style state patches (additive perf + appended errors)."""

from __future__ import annotations

from typing import Any

from app.workflows.ask_state import CopilotAskState

_ADDITIVE_FLOAT_KEYS = frozenset({"perf_transcript_fetch_ms", "perf_llm_ms"})


def merge_pipeline_state(state: CopilotAskState, patch: dict[str, Any]) -> CopilotAskState:
    """
    Apply a node patch to ``CopilotAskState``.

    - ``errors``: appended when the patch value is a non-empty list.
    - ``perf_transcript_fetch_ms``, ``perf_llm_ms``: summed (matches LangGraph reducers).
    - Other keys: last-write wins.
    """
    if not patch:
        return state
    data = state.model_dump()
    for key, value in patch.items():
        if key == "errors" and value:
            data["errors"] = list(data.get("errors") or []) + list(value)
        elif key in _ADDITIVE_FLOAT_KEYS and value is not None:
            data[key] = float(data.get(key) or 0.0) + float(value)
        else:
            data[key] = value
    return CopilotAskState.model_validate(data)

"""
Run copilot graph nodes through retrieval (same logic as ``ask_graph``) without LLM answer.

Used by streaming ask so tokens can be emitted before the verifier runs on the full raw string.
"""

from __future__ import annotations

from typing import Literal

from langchain_core.runnables import RunnableConfig

from app.workflows.ask_graph import (
    node_chunk_transcript,
    node_clean_transcript,
    node_extract_video_id,
    node_fetch_transcript,
    node_format_response,
    node_query_understanding,
    node_retrieve_context,
    node_transcript_analyst,
    node_validate_input,
)
from app.workflows.ask_state import CopilotAskState


def merge_copilot_state(state: CopilotAskState, patch: dict) -> CopilotAskState:
    """Mirror LangGraph reducer behavior for ``errors`` (append) and overwrite other keys."""
    if not patch:
        return state
    data = state.model_dump()
    for key, value in patch.items():
        if key == "errors" and value:
            data["errors"] = list(data.get("errors") or []) + list(value)
        else:
            data[key] = value
    return CopilotAskState.model_validate(data)


async def run_copilot_until_composer_ready(
    initial: CopilotAskState,
    config: RunnableConfig,
) -> tuple[CopilotAskState, Literal["early_done", "stream_llm"]]:
    """
    Execute validate → fetch → chunk → (optional) analyst → retrieve.

    Returns ``early_done`` when the non-streaming graph would jump to ``format_response``
    without calling the answer composer (validation errors, empty chunks, no retrieval hits).
    """
    s = initial

    s = merge_copilot_state(s, node_validate_input(s, config))
    if s.errors:
        s = merge_copilot_state(s, node_format_response(s, config))
        return s, "early_done"

    s = merge_copilot_state(s, node_extract_video_id(s, config))
    s = merge_copilot_state(s, node_fetch_transcript(s, config))
    s = merge_copilot_state(s, node_clean_transcript(s, config))
    s = merge_copilot_state(s, node_chunk_transcript(s, config))

    if s.errors or not s.chunks:
        s = merge_copilot_state(s, node_format_response(s, config))
        return s, "early_done"

    s = merge_copilot_state(s, node_transcript_analyst(s, config))
    s = merge_copilot_state(s, await node_query_understanding(s, config))
    s = merge_copilot_state(s, await node_retrieve_context(s, config))

    if s.errors or not s.citation_hits:
        s = merge_copilot_state(s, node_format_response(s, config))
        return s, "early_done"

    return s, "stream_llm"

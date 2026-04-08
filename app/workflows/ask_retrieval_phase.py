"""
Run copilot stages through retrieval (same logic as ``ask_graph``) without compose LLM.

Used by streaming ask so tokens can be emitted before the verifier runs on the full raw string.
"""

from __future__ import annotations

from typing import Literal

from langchain_core.runnables import RunnableConfig

from app.workflows.ask_pipeline.chunking_stage import chunk_transcript, transcript_analyst
from app.workflows.ask_pipeline.llm_stage import query_understanding
from app.workflows.ask_pipeline.postprocess_stage import format_response
from app.workflows.ask_pipeline.retrieval_stage import retrieve_context
from app.workflows.ask_pipeline.state_merge import merge_pipeline_state
from app.workflows.ask_pipeline.transcript_stage import (
    clean_transcript,
    extract_video_id,
    fetch_transcript,
    validate_input,
)
from app.workflows.ask_state import CopilotAskState


def merge_copilot_state(state: CopilotAskState, patch: dict) -> CopilotAskState:
    """Backward-compatible name for :func:`merge_pipeline_state`."""
    return merge_pipeline_state(state, patch)


async def run_copilot_until_composer_ready(
    initial: CopilotAskState,
    config: RunnableConfig,
) -> tuple[CopilotAskState, Literal["early_done", "stream_llm"]]:
    """
    Execute transcript → chunking → LLM query understanding → retrieval.

    Returns ``early_done`` when the non-streaming graph would jump to ``format_response``
    without calling the answer composer (validation errors, empty chunks, no retrieval hits).
    """
    s = initial

    s = merge_pipeline_state(s, validate_input(s, config))
    if s.errors:
        s = merge_pipeline_state(s, format_response(s, config))
        return s, "early_done"

    s = merge_pipeline_state(s, extract_video_id(s, config))
    s = merge_pipeline_state(s, fetch_transcript(s, config))
    s = merge_pipeline_state(s, clean_transcript(s, config))
    s = merge_pipeline_state(s, chunk_transcript(s, config))

    if s.errors or not s.chunks:
        s = merge_pipeline_state(s, format_response(s, config))
        return s, "early_done"

    s = merge_pipeline_state(s, transcript_analyst(s, config))
    s = merge_pipeline_state(s, await query_understanding(s, config))
    s = merge_pipeline_state(s, await retrieve_context(s, config))

    if s.errors or not s.citation_hits:
        s = merge_pipeline_state(s, format_response(s, config))
        return s, "early_done"

    return s, "stream_llm"

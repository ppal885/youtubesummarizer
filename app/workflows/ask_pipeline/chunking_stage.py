"""
Stage 2 — Chunking: segment transcript for retrieval + lightweight transcript analysis (themes).

No embedding, retrieval, or answer LLM.
"""

from __future__ import annotations

import time

from langchain_core.runnables import RunnableConfig

from app.copilot.transcript_analyst import TranscriptAnalystAgent
from app.services.chunk_service import chunk_transcript_items
from app.workflows.ask_pipeline.deps import get_ask_deps
from app.workflows.ask_state import CopilotAskState

_ANALYST = TranscriptAnalystAgent()


def chunk_transcript(state: CopilotAskState, config: RunnableConfig) -> dict:
    if state.errors:
        return {}
    t0 = time.perf_counter()
    chunks = chunk_transcript_items(state.transcript_items, get_ask_deps(config).settings)
    chunk_ms = round((time.perf_counter() - t0) * 1000, 2)
    if not chunks:
        return {
            "chunks": [],
            "answer": "No transcript text was available to search after chunking.",
            "sources": [],
            "confidence": 0.0,
            "confidence_score": 0.0,
            "perf_chunking_ms": chunk_ms,
        }
    return {"chunks": chunks, "perf_chunking_ms": chunk_ms}


def transcript_analyst(state: CopilotAskState, config: RunnableConfig) -> dict:
    _ = config
    if state.errors:
        return {}
    return {
        "transcript_analysis": _ANALYST.analyze(
            merged_transcript=state.transcript,
            chunks=state.chunks,
            video_end_seconds=state.video_end_seconds,
        )
    }


def run_chunking_stage(state: CopilotAskState, config: RunnableConfig) -> CopilotAskState:
    """Chunk + analyst in order (for tests). Skips analyst when chunking produced no chunks."""
    from app.workflows.ask_pipeline.state_merge import merge_pipeline_state

    s = merge_pipeline_state(state, chunk_transcript(state, config))
    if s.errors or not s.chunks:
        return s
    return merge_pipeline_state(s, transcript_analyst(s, config))

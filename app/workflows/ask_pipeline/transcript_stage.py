"""
Stage 1 — Transcript: validate URL/question, resolve video id, fetch captions, normalize text.

Pure state patches; no chunking or retrieval.
"""

from __future__ import annotations

import time

from langchain_core.runnables import RunnableConfig

from app.exceptions import InvalidYouTubeUrlError
from app.models.transcript_models import TranscriptItem
from app.services.transcript_service import fetch_transcript_items, merge_transcript_text
from app.services.youtube_service import extract_video_id as parse_youtube_video_id
from app.utils.text_cleaner import normalize_whitespace
from app.workflows.ask_pipeline.deps import get_ask_deps
from app.workflows.ask_state import CopilotAskState


def validate_input(state: CopilotAskState, config: RunnableConfig) -> dict:
    _ = config
    question = state.question.strip()
    url = state.url.strip()
    out: dict = {"question": question, "url": url}
    if not question:
        out["errors"] = ["Question must not be empty."]
    if not url:
        out["errors"] = ["URL must not be empty."]
    return out


def extract_video_id(state: CopilotAskState, config: RunnableConfig) -> dict:
    _ = config
    if state.errors:
        return {}
    video_id = parse_youtube_video_id(state.url)
    if video_id is None:
        raise InvalidYouTubeUrlError(
            "Could not parse a valid YouTube video id from the provided URL."
        )
    return {"video_id": video_id}


def fetch_transcript(state: CopilotAskState, config: RunnableConfig) -> dict:
    _ = config
    if state.errors:
        return {}
    assert state.video_id is not None
    t0 = time.perf_counter()
    items = fetch_transcript_items(state.video_id, state.language)
    fetch_ms = round((time.perf_counter() - t0) * 1000, 2)
    video_end = max((item.start + item.duration) for item in items) if items else 0.0
    return {
        "transcript_items": items,
        "video_end_seconds": video_end,
        "perf_transcript_fetch_ms": fetch_ms,
    }


def clean_transcript(state: CopilotAskState, config: RunnableConfig) -> dict:
    _ = config
    if state.errors:
        return {}
    t0 = time.perf_counter()
    cleaned = [
        TranscriptItem(start=item.start, duration=item.duration, text=normalize_whitespace(item.text))
        for item in state.transcript_items
    ]
    merged = merge_transcript_text(cleaned) or None
    clean_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "transcript_items": cleaned,
        "transcript": merged,
        "perf_transcript_fetch_ms": clean_ms,
    }


def run_transcript_stage(state: CopilotAskState, config: RunnableConfig) -> CopilotAskState:
    """Run all transcript substeps in order (for integration-style tests)."""
    from app.workflows.ask_pipeline.state_merge import merge_pipeline_state

    s = state
    for fn in (validate_input, extract_video_id, fetch_transcript, clean_transcript):
        s = merge_pipeline_state(s, fn(s, config))
    return s

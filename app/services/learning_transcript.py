"""
Shared transcript fetch + chunking for learning endpoints (notes / quiz / flashcards).

Produces a time-labeled transcript string so the LLM can ground outputs in caption timing,
reusing the same chunking settings as summarization.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.exceptions import InvalidYouTubeUrlError, TranscriptFetchError
from app.models.request_models import TranscriptLearningRequest
from app.models.transcript_models import TranscriptItem, TranscriptTextChunk
from app.services.chunk_service import chunk_transcript_items
from app.services.transcript_service import fetch_transcript_items, merge_transcript_text
from app.services.youtube_service import extract_video_id, fetch_video_title
from app.utils.time_utils import format_seconds_hh_mm_ss

_MAX_LABELED_TRANSCRIPT_CHARS = 18_000


@dataclass(frozen=True, slots=True)
class LearningTranscriptContext:
    """Typed bundle passed into :class:`LearningService` after transcript ingestion."""

    video_id: str
    title: str
    language: str
    items: list[TranscriptItem]
    chunks: list[TranscriptTextChunk]
    labeled_transcript: str


def format_labeled_chunks(chunks: list[TranscriptTextChunk]) -> str:
    """Join chunks with explicit timestamps (same idea as Q&A context labeling)."""
    lines: list[str] = []
    for ch in chunks:
        t = format_seconds_hh_mm_ss(ch.start_seconds)
        lines.append(f"[time={t} start_seconds={ch.start_seconds:.2f}]")
        lines.append(ch.text.strip())
        lines.append("")
    return "\n".join(lines).strip()


def load_learning_transcript_context(
    request: TranscriptLearningRequest,
    settings: Settings,
) -> LearningTranscriptContext:
    """
    Fetch captions, chunk like summarize, and build a capped labeled transcript for LLMs.

    Raises the same domain errors as other transcript flows.
    """
    url = str(request.url)
    video_id = extract_video_id(url)
    if video_id is None:
        raise InvalidYouTubeUrlError(
            "Could not parse a valid YouTube video id from the provided URL."
        )
    title = fetch_video_title(url)
    items = fetch_transcript_items(video_id, request.language)
    merged = merge_transcript_text(items)
    if not merged.strip():
        raise TranscriptFetchError("Transcript was empty after cleaning.")

    chunks = chunk_transcript_items(items, settings)
    labeled = format_labeled_chunks(chunks)
    if len(labeled) > _MAX_LABELED_TRANSCRIPT_CHARS:
        labeled = labeled[: _MAX_LABELED_TRANSCRIPT_CHARS - 1] + "…"

    return LearningTranscriptContext(
        video_id=video_id,
        title=title,
        language=request.language,
        items=list(items),
        chunks=chunks,
        labeled_transcript=labeled,
    )


def chunk_start_times(chunks: list[TranscriptTextChunk]) -> frozenset[float]:
    """Allowed anchor times for flashcard timestamp hints (seconds)."""
    return frozenset(c.start_seconds for c in chunks)

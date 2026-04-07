"""Transcript chunk helpers shared by retrieval (pgvector path uses :class:`TranscriptChunkRepository`)."""

from app.models.qa_models import TranscriptChunkPassage
from app.models.transcript_models import TranscriptTextChunk
from app.models.retrieval_models import TranscriptChunk


def passages_to_transcript_chunks(
    passages: list[TranscriptChunkPassage],
    video_end_seconds: float,
) -> list[TranscriptChunk]:
    """Derive typed chunks with end_time from ordered passages and video end."""
    if not passages:
        return []

    ordered = sorted(passages, key=lambda p: p.chunk_index)
    out: list[TranscriptChunk] = []
    for i, p in enumerate(ordered):
        if i + 1 < len(ordered):
            end_t = ordered[i + 1].start_seconds
        else:
            end_t = video_end_seconds if video_end_seconds >= p.start_seconds else None
        out.append(
            TranscriptChunk(
                chunk_id=p.chunk_index,
                text=p.text,
                start_time=p.start_seconds,
                end_time=end_t,
            )
        )
    return out


def chunk_end_times_from_items(
    text_chunks: list[TranscriptTextChunk],
    video_end_seconds: float,
) -> list[float | None]:
    """Half-open segment ends: next chunk start, else video end (or None if invalid)."""
    ends: list[float | None] = []
    n = len(text_chunks)
    for i in range(n):
        ch = text_chunks[i]
        if i + 1 < n:
            ends.append(text_chunks[i + 1].start_seconds)
        else:
            ends.append(
                video_end_seconds if video_end_seconds >= ch.start_seconds else None
            )
    return ends

"""
Chapter detection from transcript topic shifts (adjacent chunk similarity + time gaps).

Produces coarse timed segments without fixed-width windows; when segmentation is uncertain,
the pipeline returns fewer chapters (often one).
"""

from __future__ import annotations

import re
import statistics
from typing import TYPE_CHECKING

from app.models.chapter_models import ChapterSegment
from app.models.response_models import VideoChapter
from app.models.transcript_models import TranscriptTextChunk
from app.services.llm.qa_grounding import is_qa_answer_grounded
from app.services.llm.schemas import ChapterLlmItem
from app.utils.time_utils import format_seconds_hh_mm_ss

if TYPE_CHECKING:
    from app.services.llm import LLMService

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)

# Similarity / segmentation (conservative: prefer fewer, longer chapters when ambiguous).
_MIN_SIM_SINGLE_TOPIC = 0.36  # if all adjacent pairs above this → one chapter
_BOUNDARY_SIM_LOW = 0.13
_BOUNDARY_SIM_MED = 0.22
_GAP_SECONDS_STRONG = 95.0
_MIN_CHAPTER_SPAN_SEC = 45.0
_MAX_CHAPTERS = 10
_MAX_SEGMENT_CHARS = 8000
_MEDIAN_SIM_MERGE_CAP = 0.27  # noisy flat similarity → cap at 3 chapters
_SUMMARY_MAX_LEN = 500


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text) if len(t) >= 3}


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def _span_seconds(chunks: list[TranscriptTextChunk], lo: int, hi: int) -> float:
    return max(0.0, chunks[hi].start_seconds - chunks[lo].start_seconds)


def _adjacent_sims(chunks: list[TranscriptTextChunk]) -> list[float]:
    return [_jaccard(chunks[i - 1].text, chunks[i].text) for i in range(1, len(chunks))]


def detect_chapter_ranges(chunks: list[TranscriptTextChunk]) -> list[tuple[int, int]]:
    """
    Return inclusive chunk index ranges where boundaries follow low lexical continuity
    or large caption gaps (topic-shift proxy).
    """
    n = len(chunks)
    if n == 0:
        return []
    if n == 1:
        return [(0, 0)]

    sims = _adjacent_sims(chunks)
    if not sims:
        return [(0, n - 1)]

    if min(sims) > _MIN_SIM_SINGLE_TOPIC:
        return [(0, n - 1)]

    cuts: list[int] = []
    for i in range(1, n):
        s = sims[i - 1]
        gap = chunks[i].start_seconds - chunks[i - 1].start_seconds
        if s < _BOUNDARY_SIM_LOW or (s < _BOUNDARY_SIM_MED and gap >= _GAP_SECONDS_STRONG):
            cuts.append(i)

    if not cuts:
        return [(0, n - 1)]

    ranges: list[tuple[int, int]] = []
    start = 0
    for c in cuts:
        if c > start:
            ranges.append((start, c - 1))
        start = c
    ranges.append((start, n - 1))
    ranges = [r for r in ranges if r[0] <= r[1]]

    ranges = _merge_short_spans(ranges, chunks)
    ranges = _cap_chapter_count(ranges, sims, max_chapters=_MAX_CHAPTERS)

    if sims and statistics.median(sims) > _MEDIAN_SIM_MERGE_CAP and len(ranges) > 3:
        ranges = _cap_chapter_count(ranges, sims, max_chapters=3)

    return ranges if ranges else [(0, n - 1)]


def _merge_short_spans(
    ranges: list[tuple[int, int]],
    chunks: list[TranscriptTextChunk],
) -> list[tuple[int, int]]:
    changed = True
    while changed and len(ranges) > 1:
        changed = False
        for i, (lo, hi) in enumerate(ranges):
            if _span_seconds(chunks, lo, hi) >= _MIN_CHAPTER_SPAN_SEC:
                continue
            if i > 0:
                pl, ph = ranges[i - 1]
                ranges[i - 1] = (pl, hi)
                ranges.pop(i)
                changed = True
                break
            if i + 1 < len(ranges):
                nlo, nhi = ranges[i + 1]
                ranges[i] = (lo, nhi)
                ranges.pop(i + 1)
                changed = True
                break
    return ranges


def _cap_chapter_count(
    ranges: list[tuple[int, int]],
    sims: list[float],
    *,
    max_chapters: int,
) -> list[tuple[int, int]]:
    while len(ranges) > max_chapters:
        best_i: int | None = None
        best_sim = -1.0
        for i in range(len(ranges) - 1):
            _, b = ranges[i]
            if b >= len(sims):
                continue
            s = sims[b]
            if s > best_sim:
                best_sim = s
                best_i = i
        if best_i is None:
            break
        a, b = ranges[best_i]
        _, d = ranges[best_i + 1]
        ranges[best_i] = (a, d)
        ranges.pop(best_i + 1)
    return ranges


def build_segments(
    chunks: list[TranscriptTextChunk],
    ranges: list[tuple[int, int]],
) -> list[ChapterSegment]:
    segs: list[ChapterSegment] = []
    for lo, hi in ranges:
        parts = [chunks[i].text.strip() for i in range(lo, hi + 1) if chunks[i].text.strip()]
        text = " ".join(parts)
        if len(text) > _MAX_SEGMENT_CHARS:
            text = f"{text[: _MAX_SEGMENT_CHARS - 1]}…"
        if not text:
            text = "—"
        segs.append(
            ChapterSegment(
                start_seconds=chunks[lo].start_seconds,
                text=text,
            )
        )
    return segs


def _ground_summary(summary: str, source: str) -> str:
    from app.models.qa_models import TranscriptChunkPassage

    stripped = summary.strip()
    if not stripped:
        return _fallback_summary(source)
    passage = TranscriptChunkPassage(
        id=0,
        chunk_index=0,
        start_seconds=0.0,
        text=source,
    )
    if is_qa_answer_grounded(stripped, [passage]):
        return stripped[:_SUMMARY_MAX_LEN]
    return _fallback_summary(source)


def _fallback_summary(source: str) -> str:
    one_line = source.strip().replace("\n", " ")
    if len(one_line) > 220:
        return f"{one_line[:219]}…"
    return one_line or "—"


async def build_video_chapters(
    chunks: list[TranscriptTextChunk],
    llm: LLMService,
) -> list[VideoChapter]:
    """End-to-end: segment by topic shift, then LLM labels (grounded + trimmed)."""
    if not chunks:
        return []

    ranges = detect_chapter_ranges(chunks)
    segments = build_segments(chunks, ranges)
    if not segments:
        return []

    llm_items = await llm.generate_chapters(segments)
    n = len(segments)
    if len(llm_items) < n:
        llm_items = list(llm_items)
        while len(llm_items) < n:
            idx = len(llm_items)
            llm_items.append(
                ChapterLlmItem(
                    title=f"Part {idx + 1}",
                    short_summary="",
                )
            )
    elif len(llm_items) > n:
        llm_items = llm_items[:n]

    out: list[VideoChapter] = []
    for seg, item in zip(segments, llm_items, strict=True):
        title = (item.title or "").strip() or "Untitled segment"
        summ = _ground_summary(item.short_summary, seg.text)
        st = seg.start_seconds
        out.append(
            VideoChapter(
                title=title[:200],
                start_time=st,
                formatted_time=format_seconds_hh_mm_ss(st),
                short_summary=summ,
            )
        )
    return out

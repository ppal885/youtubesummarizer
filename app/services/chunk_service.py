"""
Transcript chunking for LLM calls.

Uses sentence-boundary-aware packing with a fixed overlap. When ``CHUNK_USE_TOKENS``
is enabled and :mod:`tiktoken` loads correctly, chunk size and overlap are measured in
tokens; otherwise (or if tiktoken fails) the implementation falls back to character
measurement using ``MAX_CHUNK_CHARS`` / ``CHUNK_OVERLAP_CHARS``.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, NamedTuple

from app.config import Settings
from app.models.transcript_models import TranscriptItem, TranscriptTextChunk
from app.utils.text_cleaner import normalize_whitespace


class CaptionCharSpan(NamedTuple):
    """Inclusive-exclusive character range in merged transcript text."""

    start_char: int
    end_char: int
    start_seconds: float


# Splits after sentence-ending punctuation followed by whitespace (MVP heuristic).
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def _build_merged_spans(items: list[TranscriptItem]) -> tuple[str, list[CaptionCharSpan]]:
    """Build merged transcript text and per-line character spans."""
    pieces: list[tuple[str, float]] = []
    for item in items:
        normalized = normalize_whitespace(item.text)
        if normalized:
            pieces.append((normalized, item.start))

    if not pieces:
        return "", []

    spans: list[CaptionCharSpan] = []
    offset = 0
    token_strings: list[str] = []
    for index, (text, start_seconds) in enumerate(pieces):
        start_idx = offset
        end_idx = offset + len(text)
        spans.append(CaptionCharSpan(start_idx, end_idx, start_seconds))
        token_strings.append(text)
        offset = end_idx
        if index < len(pieces) - 1:
            offset += 1

    merged = " ".join(token_strings)
    return merged, spans


def _start_seconds_for_char(spans: list[CaptionCharSpan], char_index: int) -> float:
    for span in spans:
        if span.end_char > char_index:
            return span.start_seconds
    if spans:
        return spans[-1].start_seconds
    return 0.0


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """
    Split ``text`` into half-open ``[start, end)`` spans at sentence-like boundaries.

    Uses punctuation (``.?!``) followed by whitespace. If there are no such breaks,
    returns a single span covering the non-empty text. Purely whitespace input yields
    an empty list.
    """
    if not text.strip():
        return []

    spans: list[tuple[int, int]] = []
    start = 0
    for match in _SENTENCE_BOUNDARY.finditer(text):
        end = match.start()
        if end > start:
            spans.append((start, end))
        start = match.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def _first_sentence_index_covering(spans: list[tuple[int, int]], pos: int) -> int:
    for idx, (_, end) in enumerate(spans):
        if end > pos:
            return idx
    return len(spans)


def _max_end_under_budget(
    merged: str,
    lo: int,
    hi: int,
    max_units: int,
    measure: Callable[[str], int],
) -> int:
    """Largest ``end`` in ``[lo, hi]`` with ``measure(merged[lo:end]) <= max_units``."""
    if lo >= hi:
        return lo
    best = lo
    left, right = lo, hi
    while left <= right:
        mid = (left + right) // 2
        if measure(merged[lo:mid]) <= max_units:
            best = mid
            left = mid + 1
        else:
            right = mid - 1
    if best == lo and lo < hi:
        return min(lo + 1, hi)
    return best


def _next_overlap_start(
    merged: str,
    chunk_start: int,
    chunk_end: int,
    overlap_units: int,
    encoder: Any | None,
) -> int:
    """
    First character index where the next chunk should start so that it shares roughly
    ``overlap_units`` tokens (if ``encoder`` is set) or characters (if ``encoder`` is None)
    with ``merged[chunk_start:chunk_end]``.

    Deterministic: token overlap is defined by dropping the first ``len(ids) - k`` tokens
    from the previous chunk (``k = min(overlap_units, len(ids)-1)``).
    """
    if overlap_units <= 0 or chunk_end <= chunk_start:
        return chunk_end

    prev = merged[chunk_start:chunk_end]
    if encoder is None:
        return max(chunk_start, chunk_end - overlap_units)

    ids: list[int] = encoder.encode(prev)
    if not ids:
        return chunk_end
    k = min(overlap_units, max(0, len(ids) - 1))
    if k <= 0:
        return chunk_end
    prefix: str = encoder.decode(ids[: len(ids) - k])
    return chunk_start + len(prefix)


def _resolve_measurer(
    settings: Settings,
) -> tuple[Callable[[str], int], int, int, Any | None]:
    """
    Return ``(measure, max_units, overlap_units, encoder)``.

    ``encoder`` is a tiktoken ``Encoding`` when token mode is active and tiktoken works;
    otherwise ``None`` and character limits from settings are used.
    """
    max_chars = settings.max_chunk_chars
    overlap_chars = settings.chunk_overlap_chars
    if overlap_chars >= max_chars:
        overlap_chars = max(0, max_chars - 1)

    if not settings.chunk_use_tokens:
        return (len, max_chars, overlap_chars, None)

    try:
        import tiktoken

        enc = tiktoken.get_encoding(settings.chunk_token_encoding)
    except Exception:
        return len, max_chars, overlap_chars, None

    max_tok = settings.max_chunk_tokens
    overlap_tok = settings.chunk_overlap_tokens
    if overlap_tok >= max_tok:
        overlap_tok = max(0, max_tok - 1)

    def measure_tokens(t: str) -> int:
        return len(enc.encode(t))

    return measure_tokens, max_tok, overlap_tok, enc


def _fixed_fallback_ranges(
    text: str,
    chunk_size: int,
    overlap: int,
) -> list[tuple[int, int]]:
    """Original character sliding-window ranges (deterministic)."""
    if chunk_size <= 0:
        raise ValueError("chunk size must be positive")
    if not text:
        return []

    effective_overlap = max(0, min(overlap, chunk_size - 1)) if chunk_size > 1 else 0
    ranges: list[tuple[int, int]] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        ranges.append((start, end))
        if end >= length:
            break
        start = end - effective_overlap
    return ranges


def chunk_ranges(
    merged: str,
    settings: Settings,
) -> list[tuple[int, int]]:
    """
    Compute ordered, half-open ``[start, end)`` chunk ranges over ``merged`` text.

    Sentence boundaries are preferred when packing. Overlap is applied deterministically
    after each chunk. If ``merged`` is empty, returns ``[]``. If sentence detection yields
    no spans (rare for non-empty text), falls back to pure character windows.
    """
    measure, max_units, overlap_units, encoder = _resolve_measurer(settings)

    if not merged.strip():
        return []

    spans = sentence_spans(merged)
    if not spans:
        return _fixed_fallback_ranges(merged, settings.max_chunk_chars, settings.chunk_overlap_chars)

    ranges: list[tuple[int, int]] = []
    pos = 0
    n = len(merged)
    iterations = 0
    max_iterations = max(1, n * 2)

    while pos < n:
        iterations += 1
        if iterations > max_iterations:
            break

        while pos < n and merged[pos].isspace():
            pos += 1
        if pos >= n:
            break

        first_j = _first_sentence_index_covering(spans, pos)
        chunk_start = pos
        chunk_end = chunk_start
        j = first_j
        while j < len(spans):
            _, end_j = spans[j]
            candidate = merged[chunk_start:end_j]
            if measure(candidate) <= max_units:
                chunk_end = end_j
                j += 1
            else:
                break

        if chunk_end == chunk_start:
            sj, ej = spans[first_j]
            lo = max(chunk_start, sj)
            hi = max(lo + 1, ej)
            chunk_end = _max_end_under_budget(merged, lo, hi, max_units, measure)
            if chunk_end <= chunk_start:
                chunk_end = min(chunk_start + 1, n)

        ranges.append((chunk_start, chunk_end))

        next_pos = _next_overlap_start(merged, chunk_start, chunk_end, overlap_units, encoder)
        if next_pos >= chunk_end:
            next_pos = chunk_end
        if next_pos <= ranges[-1][0]:
            next_pos = chunk_end
        pos = next_pos

    if not ranges and merged.strip():
        return [(0, len(merged))]

    return ranges


def chunk_transcript_items(
    items: list[TranscriptItem],
    settings: Settings,
) -> list[TranscriptTextChunk]:
    """
    Turn caption items into ``TranscriptTextChunk`` slices for summarization.

    Uses :func:`chunk_ranges` (sentence-aware packing, optional token budgets via
    tiktoken, deterministic overlap). Empty transcript input yields an empty list;
    a single non-empty chunk is emitted when the merged text is non-empty but splitting
    produces no usable windows.
    """
    merged, caption_spans = _build_merged_spans(items)

    if not merged.strip():
        return []

    ranges = chunk_ranges(merged, settings)

    if not ranges and merged.strip():
        ranges = [(0, len(merged))]

    chunks: list[TranscriptTextChunk] = []
    for range_start, range_end in ranges:
        slice_text = merged[range_start:range_end]
        if not slice_text.strip():
            continue
        start_seconds = _start_seconds_for_char(caption_spans, range_start)
        chunks.append(TranscriptTextChunk(text=slice_text, start_seconds=start_seconds))

    if not chunks and merged.strip():
        chunks.append(
            TranscriptTextChunk(
                text=merged.strip(),
                start_seconds=_start_seconds_for_char(caption_spans, 0),
            )
        )

    return chunks

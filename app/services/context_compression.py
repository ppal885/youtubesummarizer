"""
RAG context compression: wide retrieval pool -> 3-5 labeled passages for the answer LLM.

Heuristic mode merges ranked hits by contiguous groups; LLM mode uses one structured call.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from app.config import Settings
from app.models.qa_models import TranscriptChunkPassage
from app.models.retrieval_models import RetrievalHit
from app.services.llm.schemas import CompressedQaContextItemPayload, CompressedQaContextPayload
from app.utils.time_utils import format_seconds_hh_mm_ss

if TYPE_CHECKING:
    from app.services.llm.base import LLMService

_LOG = logging.getLogger(__name__)

_CITATION_SLICE = 3
_HEURISTIC_CHARS_PER_BLOCK = 1000


def _split_sizes(n: int, k: int) -> list[int]:
    if k <= 0 or n <= 0:
        return []
    base, rem = divmod(n, k)
    return [base + (1 if i < rem else 0) for i in range(k)]


def _heuristic_groups(hits: list[RetrievalHit], target: int) -> list[list[RetrievalHit]]:
    n = len(hits)
    if n <= target:
        return [[h] for h in hits]
    sizes = _split_sizes(n, target)
    groups: list[list[RetrievalHit]] = []
    offset = 0
    for size in sizes:
        groups.append(hits[offset : offset + size])
        offset += size
    return groups


def _truncate_block(text: str, max_len: int) -> str:
    stripped = text.strip()
    if len(stripped) <= max_len:
        return stripped
    cut = stripped[: max_len - 3]
    space = cut.rfind(" ")
    if space > max_len // 2:
        cut = cut[:space]
    return f"{cut}..."


def _passage_from_group(
    group: list[RetrievalHit],
    *,
    chars_per_block: int = _HEURISTIC_CHARS_PER_BLOCK,
) -> TranscriptChunkPassage:
    first = group[0].passage
    last = group[-1].passage
    start_seconds = min(hit.passage.start_seconds for hit in group)
    chunk_index = min(hit.passage.chunk_index for hit in group)
    passage_id = min(hit.passage.id for hit in group)
    merged = "\n\n".join(hit.passage.text.strip() for hit in group if hit.passage.text.strip())
    span = f"({first.time_display}-{last.time_display})"
    body = _truncate_block(merged, max(200, chars_per_block - len(span) - 2))
    text = f"{span}\n{body}" if span else body
    return TranscriptChunkPassage(
        id=passage_id,
        chunk_index=chunk_index,
        start_seconds=start_seconds,
        text=text,
    )


def _synthetic_hit_from_group(group: list[RetrievalHit], passage: TranscriptChunkPassage) -> RetrievalHit:
    return RetrievalHit(
        passage=passage,
        semantic_score=max(hit.semantic_score for hit in group),
        keyword_score=max(hit.keyword_score for hit in group),
        final_score=max(hit.final_score for hit in group),
        ranking_explanation="compressed_context",
    )


def compress_heuristic(
    hits: list[RetrievalHit],
    target: int,
    *,
    chars_per_block: int = _HEURISTIC_CHARS_PER_BLOCK,
) -> tuple[list[TranscriptChunkPassage], list[RetrievalHit]]:
    """Merge ranked hits into ``target`` contiguous groups; preserve earliest timestamp per group."""
    if not hits:
        return [], []
    passages: list[TranscriptChunkPassage] = []
    synthetic_hits: list[RetrievalHit] = []
    for group in _heuristic_groups(hits, target):
        if not group:
            continue
        passage = _passage_from_group(group, chars_per_block=chars_per_block)
        passages.append(passage)
        synthetic_hits.append(_synthetic_hit_from_group(group, passage))
    return passages, synthetic_hits


def heuristic_compressed_payload(hits: list[RetrievalHit], target_count: int) -> CompressedQaContextPayload:
    """Build the same structure an LLM would return, using heuristic grouping (for mock provider)."""
    items: list[CompressedQaContextItemPayload] = []
    for group in _heuristic_groups(hits, target_count):
        if not group:
            continue
        passage = _passage_from_group(group)
        start_seconds = min(hit.passage.start_seconds for hit in group)
        end_seconds = max(hit.passage.start_seconds for hit in group)
        items.append(
            CompressedQaContextItemPayload(
                summary=passage.text,
                source_chunk_indices=[hit.passage.chunk_index for hit in group],
                time_start_seconds=start_seconds,
                time_end_seconds=end_seconds if end_seconds > start_seconds else None,
            )
        )
    return CompressedQaContextPayload(items=items)


def _hits_by_chunk_index(hits: list[RetrievalHit]) -> dict[int, RetrievalHit]:
    return {hit.passage.chunk_index: hit for hit in hits}


def map_llm_payload_to_context(
    payload: CompressedQaContextPayload,
    source_hits: list[RetrievalHit],
    target: int,
) -> tuple[list[TranscriptChunkPassage], list[RetrievalHit]] | None:
    """Map model JSON to passages and synthetic hits; return ``None`` if invalid."""
    by_index = _hits_by_chunk_index(source_hits)
    raw_items = list(payload.items)
    if len(raw_items) < 3:
        return None

    passages: list[TranscriptChunkPassage] = []
    synthetic_hits: list[RetrievalHit] = []
    for item in raw_items[:target]:
        group: list[RetrievalHit] = []
        for chunk_index in item.source_chunk_indices:
            hit = by_index.get(chunk_index)
            if hit is None:
                return None
            group.append(hit)
        if not group:
            return None

        start_seconds = item.time_start_seconds
        min_chunk_index = min(hit.passage.chunk_index for hit in group)
        min_passage_id = min(hit.passage.id for hit in group)
        summary = item.summary.strip()
        if not summary:
            return None
        if item.time_end_seconds is not None and item.time_end_seconds > start_seconds:
            span = f"({format_seconds_hh_mm_ss(start_seconds)}-{format_seconds_hh_mm_ss(item.time_end_seconds)})"
        else:
            span = f"({format_seconds_hh_mm_ss(start_seconds)})"
        text = summary if summary.startswith("(") else f"{span}\n{summary}"
        passage = TranscriptChunkPassage(
            id=min_passage_id,
            chunk_index=min_chunk_index,
            start_seconds=start_seconds,
            text=text,
        )
        passages.append(passage)
        synthetic_hits.append(_synthetic_hit_from_group(group, passage))

    if len(passages) < 3:
        return None
    return passages, synthetic_hits


async def compress_ranked_hits(
    question: str,
    hits: list[RetrievalHit],
    *,
    settings: Settings,
    llm: LLMService,
) -> tuple[list[TranscriptChunkPassage], list[RetrievalHit], float]:
    """
    Produce answer-context passages and parallel synthetic citation hits.

    When ``len(hits) <= target``, return raw passages and hits without merge.

    Third tuple element is milliseconds spent in the LLM compression call when used; otherwise ``0.0``.
    """
    target = settings.qa_context_compress_to
    if not hits:
        return [], [], 0.0
    if len(hits) <= target:
        return [hit.passage for hit in hits], list(hits), 0.0

    llm_compress_ms = 0.0
    if settings.qa_context_compression == "llm":
        t_llm = time.perf_counter()
        try:
            payload = await llm.compress_qa_retrieval_context(question, hits, target)
            llm_compress_ms = round((time.perf_counter() - t_llm) * 1000, 2)
            mapped = map_llm_payload_to_context(payload, hits, target)
            if mapped is not None:
                passages, synthetic_hits = mapped
                return passages, synthetic_hits, llm_compress_ms
        except Exception as exc:  # noqa: BLE001
            llm_compress_ms = round((time.perf_counter() - t_llm) * 1000, 2)
            _LOG.warning("LLM context compression failed; falling back to heuristic: %s", exc)

    passages, synthetic_hits = compress_heuristic(hits, target)
    return passages, synthetic_hits, llm_compress_ms


def slice_citation_hits(synth_hits: list[RetrievalHit], limit: int = _CITATION_SLICE) -> list[RetrievalHit]:
    """Top-N synthetic hits for API ``sources``."""
    return synth_hits[:limit]

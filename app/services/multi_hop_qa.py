"""
Multi-hop Q&A: detect when answers should combine several transcript segments, guide the composer,
expand compressed context into per-chunk evidence when needed, and lightly penalize confidence
if multi-source synthesis was required but timestamps were not cited.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.models.qa_models import TranscriptChunkPassage
from app.models.retrieval_models import RetrievalHit

_MAX_HITS_FOR_DISTINCT_COUNT = 32
_MAX_UNROLLED_SEGMENTS_DEFAULT = 6
_MAX_CHARS_PER_UNROLLED_SEGMENT = 1_200


class MultiHopAssessment(BaseModel):
    """Signals whether the question/context calls for combining multiple retrieval segments."""

    requires_multi_source: bool = Field(
        ...,
        description="True when the pipeline should instruct the model to synthesize across segments.",
    )
    distinct_evidence_segments: int = Field(
        ...,
        ge=0,
        description="Distinct chunk_index values in the top of the retrieval pool.",
    )
    synthesis_instruction: str = Field(
        default="",
        description="Non-evidence user-message block appended before CONTEXT (empty when not required).",
    )


def _question_suggests_multi_segment(q: str) -> bool:
    ql = q.lower().strip()
    if not ql:
        return False
    if any(
        phrase in ql
        for phrase in (
            "difference between",
            "compared to",
            "compared with",
            " versus ",
            " vs ",
            " vs.",
            "both ",
            " as well as ",
            "relationship between",
            "how are ",
            "how do ",
            " relate ",
            "related to",
            "connect ",
            "connection between",
            "summarize",
            "summary of",
            "overview",
            "timeline",
            "sequence of",
            "step by step",
            "first ",
            " then ",
            "after that",
            "before and after",
        )
    ):
        return True
    if " and " in ql and len(ql) > 30:
        return True
    return False


def _distinct_chunks_in_pool(hits: list[RetrievalHit]) -> int:
    if not hits:
        return 0
    slice_hits = hits[:_MAX_HITS_FOR_DISTINCT_COUNT]
    return len({h.passage.chunk_index for h in slice_hits})


def _synthesis_user_block(n_segments: int) -> str:
    return (
        "MULTI-HOP / MULTI-SOURCE (instructions only — not facts; ground every claim in CONTEXT):\n"
        f"- Retrieval surfaced **{n_segments}** distinct transcript segment(s) (different chunk_index / times).\n"
        "- Read **all** CONTEXT blocks before answering. If the question needs facts from more than one time range, "
        "you MUST chain them: state what one segment establishes, then what another adds or contrasts.\n"
        "- Each substantive claim that comes from a different block must cite that block's `time=` from the header "
        "in parentheses, e.g. (01:23) or (1:02:03). When more than one block is relevant, cite **at least two** "
        "distinct timestamps (unless only one block actually supports the answer).\n"
        "- Do not merge or invent events across blocks; only link what each block actually says.\n"
        "- If CONTEXT does not support the full question, reply exactly: Not mentioned in video\n"
        "- No outside knowledge."
    )


def assess_multi_hop(
    question: str,
    selected_passages: list[TranscriptChunkPassage],
    retrieval_hits: list[RetrievalHit],
    *,
    query_intent: str | None = None,
) -> MultiHopAssessment:
    """
    Decide whether to activate multi-hop answering using the wide retrieval pool + question shape.

    ``selected_passages`` may merge chunks; the pool is authoritative for how many segments exist.
    ``query_intent`` (from query understanding) can force synthesis for comparison-style questions.
    """
    distinct_pool = _distinct_chunks_in_pool(retrieval_hits)
    if distinct_pool < 2:
        return MultiHopAssessment(
            requires_multi_source=False,
            distinct_evidence_segments=distinct_pool,
            synthesis_instruction="",
        )

    multi_q = _question_suggests_multi_segment(question)
    distinct_in_selected = len({p.chunk_index for p in selected_passages}) if selected_passages else 0
    intent = (query_intent or "").strip().lower()
    comparison_pull = intent == "comparison" and distinct_pool >= 2
    conceptual_pull = intent == "conceptual" and distinct_pool >= 3
    requires = (
        multi_q
        or distinct_in_selected >= 2
        or distinct_pool >= 4
        or comparison_pull
        or conceptual_pull
    )

    if not requires:
        return MultiHopAssessment(
            requires_multi_source=False,
            distinct_evidence_segments=distinct_pool,
            synthesis_instruction="",
        )

    return MultiHopAssessment(
        requires_multi_source=True,
        distinct_evidence_segments=distinct_pool,
        synthesis_instruction=_synthesis_user_block(distinct_pool),
    )


def build_answer_context_for_multi_hop(
    assessment: MultiHopAssessment,
    compressed_passages: list[TranscriptChunkPassage],
    retrieval_hits: list[RetrievalHit],
    *,
    max_segments: int = _MAX_UNROLLED_SEGMENTS_DEFAULT,
    max_chars_per_segment: int = _MAX_CHARS_PER_UNROLLED_SEGMENT,
) -> list[TranscriptChunkPassage]:
    """
    Passages fed to the answer LLM and verifier.

    When multi-source answering is active but compression collapsed everything into one synthetic block,
    unroll the top ranked hits into one passage per distinct ``chunk_index`` so the model sees separate
    timestamps and can combine evidence without hallucinating bridges.
    """
    if not compressed_passages:
        return []
    if not assessment.requires_multi_source:
        return list(compressed_passages)

    distinct_in_compressed = len({p.chunk_index for p in compressed_passages})
    if distinct_in_compressed >= 2:
        return list(compressed_passages)
    if assessment.distinct_evidence_segments < 2:
        return list(compressed_passages)

    seen: set[int] = set()
    out: list[TranscriptChunkPassage] = []
    for h in retrieval_hits:
        p = h.passage
        idx = p.chunk_index
        if idx in seen:
            continue
        seen.add(idx)
        text = p.text.strip()
        if len(text) > max_chars_per_segment:
            text = f"{text[: max_chars_per_segment - 1]}…"
        out.append(p.model_copy(update={"text": text}))
        if len(out) >= max_segments:
            break

    return out if len(out) >= 2 else list(compressed_passages)


_TIME_IN_PARENS_RE = re.compile(
    r"\(\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*\)",
)


def _normalize_time_token(t: str) -> str:
    parts = t.strip().split(":")
    if len(parts) == 2:
        m, s = parts[0].lstrip("0") or "0", parts[1]
        return f"{m}:{s.zfill(2)}"
    if len(parts) == 3:
        h, m, s = parts[0].lstrip("0") or "0", parts[1].lstrip("0") or "0", parts[2]
        return f"{h}:{m.zfill(2)}:{s.zfill(2)}"
    return t.strip()


def count_distinct_passages_cited_by_time(answer: str, passages: list[TranscriptChunkPassage]) -> int:
    """How many context passages appear cited via (timestamp) or a literal time_display substring."""
    if not answer.strip():
        return 0
    paren_norms = {_normalize_time_token(m.group(1)) for m in _TIME_IN_PARENS_RE.finditer(answer)}
    cited = 0
    for p in passages:
        td = p.time_display.strip()
        if _normalize_time_token(td) in paren_norms:
            cited += 1
            continue
        if td and td in answer:
            cited += 1
    return cited


def adjust_confidence_for_multi_hop(
    answer: str,
    passages: list[TranscriptChunkPassage],
    confidence: float,
    assessment: MultiHopAssessment | None,
) -> float:
    """
    If multi-source synthesis was required and context has 2+ segments, expect multiple time citations.

    Does not replace grounding checks; only scales confidence when citations are thin.
    """
    if assessment is None or not assessment.requires_multi_source:
        return confidence
    if answer.strip() == "Not mentioned in video":
        return confidence
    distinct_ctx = len({p.chunk_index for p in passages})
    if distinct_ctx < 2:
        return confidence
    cited = count_distinct_passages_cited_by_time(answer, passages)
    if cited >= 2:
        return confidence
    return max(0.35, round(confidence * 0.72, 3))

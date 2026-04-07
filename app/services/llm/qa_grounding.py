"""Post-generation checks that Q&A answers stay tied to retrieved transcript text."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.qa_models import TranscriptChunkPassage

# Model must use this exact wording when CONTEXT is insufficient (prompt-enforced).
NOT_MENTIONED_PHRASE = "Not mentioned in video"

_NOT_MENTIONED_ALIASES: frozenset[str] = frozenset(
    {
        "not mentioned in video",
        "not mentioned in the video",
        "not found in context",
        "not found in the context",
        "no transcript passages were retrieved",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_LOW_OVERLAP_THRESHOLD = 0.22
_REJECT_OVERLAP_THRESHOLD = 0.08


@dataclass(frozen=True, slots=True)
class QaGroundingResult:
    final_answer: str
    confidence: float
    confidence_score: float
    accepted: bool
    low_confidence: bool
    notes: str | None = None


def _significant_tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if len(t) >= 3]


def _is_explicit_not_mentioned(answer: str) -> bool:
    normalized = answer.strip().lower()
    compact = re.sub(r"[\s'\"`]+", " ", normalized)
    return any(alias in compact for alias in _NOT_MENTIONED_ALIASES)


def overlap_confidence_score(answer: str, passages: list[TranscriptChunkPassage]) -> float:
    """Return lexical overlap ratio in [0, 1] between answer terms and retrieved context."""
    stripped = answer.strip()
    if not stripped or _is_explicit_not_mentioned(stripped):
        return 0.0
    context = " ".join(p.text for p in passages)
    context_lower = context.lower()
    if len(stripped) <= 40 and stripped.lower() in context_lower:
        return 1.0
    ctx_tokens = set(_significant_tokens(context))
    ans_tokens = _significant_tokens(stripped)
    if not ans_tokens:
        return 0.0
    overlap = sum(1 for t in ans_tokens if t in ctx_tokens)
    return round(min(1.0, overlap / len(ans_tokens)), 3)


def _grounding_confidence_from_score(score: float) -> float:
    """Map accepted overlap strength to [0.35, 1.0]."""
    return round(0.35 + 0.65 * min(1.0, max(0.0, score)), 3)


def evaluate_qa_answer(
    answer: str,
    passages: list[TranscriptChunkPassage],
) -> QaGroundingResult:
    """Normalize the answer, score lexical support, and decide accept / low-confidence / reject."""
    stripped = answer.strip()
    if _is_explicit_not_mentioned(stripped):
        return QaGroundingResult(
            final_answer=NOT_MENTIONED_PHRASE,
            confidence=0.0,
            confidence_score=0.0,
            accepted=True,
            low_confidence=False,
            notes="explicit_not_mentioned",
        )

    score = overlap_confidence_score(stripped, passages)
    if score < _REJECT_OVERLAP_THRESHOLD:
        return QaGroundingResult(
            final_answer=rejection_answer(),
            confidence=0.0,
            confidence_score=score,
            accepted=False,
            low_confidence=False,
            notes="rejected_low_overlap",
        )
    if score < _LOW_OVERLAP_THRESHOLD:
        return QaGroundingResult(
            final_answer=stripped,
            confidence=score,
            confidence_score=score,
            accepted=True,
            low_confidence=True,
            notes="low_overlap",
        )
    return QaGroundingResult(
        final_answer=stripped,
        confidence=_grounding_confidence_from_score(score),
        confidence_score=score,
        accepted=True,
        low_confidence=False,
        notes=None,
    )


def postprocess_qa_answer(
    answer: str,
    passages: list[TranscriptChunkPassage],
) -> tuple[str, float]:
    """
    Normalize refusal wording, validate support against retrieved chunks, and assign confidence.

    Returns ``(final_answer, confidence)`` with confidence in [0, 1].
    """
    result = evaluate_qa_answer(answer, passages)
    return result.final_answer, result.confidence


def is_qa_answer_grounded(answer: str, passages: list[TranscriptChunkPassage]) -> bool:
    """
    Return True if the answer either (a) explicitly states missing coverage, or
    (b) shares lexical overlap with the retrieved chunks (guards against unrelated text).
    """
    if _is_explicit_not_mentioned(answer):
        return True
    return overlap_confidence_score(answer, passages) >= _REJECT_OVERLAP_THRESHOLD


def rejection_answer() -> str:
    return NOT_MENTIONED_PHRASE

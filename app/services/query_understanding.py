"""
Query classification and retrieval-oriented rewriting for transcript Q&A.

The viewer's original question is preserved for the answer composer; ``retrieval_query`` in graph state
feeds hybrid retrieval, re-ranking overlap, and context compression.
"""

from __future__ import annotations

from typing import Literal

from app.exceptions import LLMInvocationError
from app.services.llm.base import LLMService
from app.services.llm.schemas import QaQueryUnderstandingPayload, QueryUnderstandingIntent

QueryIntent = QueryUnderstandingIntent

__all__ = [
    "QueryIntent",
    "heuristic_query_understanding",
    "merge_retrieval_query_text",
    "run_query_understanding",
]


def merge_retrieval_query_text(payload: QaQueryUnderstandingPayload, *, fallback: str) -> str:
    """Combine normalized phrasing and expansion keywords; fall back to the raw question if needed."""
    base = payload.normalized_query.strip()
    extras = [k.strip() for k in payload.expansion_keywords if k and k.strip()]
    extra_s = " ".join(extras)
    if base and extra_s:
        return f"{base} {extra_s}"
    if base:
        return base
    if extra_s:
        return extra_s
    return fallback.strip()


def heuristic_query_understanding(question: str) -> QaQueryUnderstandingPayload:
    """Fast offline intent guess + light normalization when the LLM is unavailable or fails."""
    raw = question.strip()
    q_lower = raw.lower()
    if not q_lower:
        return QaQueryUnderstandingPayload(
            intent="factual",
            normalized_query=".",
            expansion_keywords=[],
        )

    intent: Literal["factual", "conceptual", "comparison", "definition"] = "factual"
    if any(
        phrase in q_lower
        for phrase in (
            " vs ",
            " versus ",
            " v ",
            "compare ",
            "comparison",
            "difference between",
            "differences between",
            "better than",
            " or ",
        )
    ):
        intent = "comparison"
    elif q_lower.startswith(
        ("what is ", "what are ", "what was ", "what were ", "define ", "definition of ", "meaning of ")
    ) or q_lower.startswith("who is ") or q_lower.startswith("who are "):
        intent = "definition"
    elif any(
        q_lower.startswith(prefix)
        for prefix in (
            "why ",
            "how does ",
            "how do ",
            "how did ",
            "explain ",
            "what does it mean",
            "what is meant",
        )
    ) or "how it works" in q_lower:
        intent = "conceptual"

    normalized = raw
    for noise in ("in this video", "from the video", "in the video", "please ", "can you tell me "):
        normalized = normalized.replace(noise, " ")
    normalized = " ".join(normalized.split())

    keywords: list[str] = []
    for prefix in ("what is ", "what are ", "define ", "definition of ", "meaning of "):
        if q_lower.startswith(prefix):
            tail = raw[len(prefix) :].strip().rstrip("?").strip()
            if tail and len(tail) > 1:
                keywords.append(tail)
            break

    return QaQueryUnderstandingPayload(
        intent=intent,
        normalized_query=normalized if normalized else raw,
        expansion_keywords=keywords[:12],
    )


async def run_query_understanding(question: str, llm: LLMService) -> QaQueryUnderstandingPayload:
    """LLM-based understanding with heuristic fallback (never raises)."""
    q = question.strip()
    if not q:
        return heuristic_query_understanding(question)
    try:
        return await llm.understand_qa_query(q)
    except (LLMInvocationError, ValueError, TypeError):
        return heuristic_query_understanding(q)

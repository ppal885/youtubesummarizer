"""Lightweight lexical metrics (no extra LLM calls) for portfolio evaluation."""

from __future__ import annotations

import re

from app.models.retrieval_models import RetrievalHit

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def significant_tokens(text: str) -> list[str]:
    """Same tokenization spirit as ``qa_grounding`` (length ≥ 3 alnum tokens)."""
    return [t.lower() for t in _TOKEN_RE.findall(text) if len(t) >= 3]


def lexical_support_ratio(generated: str, evidence: str) -> float:
    """
    Fraction of generated tokens that appear in evidence (0–1).

    Used for summary faithfulness (evidence = transcript) and retrieval relevance
    (evidence = retrieved passages).
    """
    ev = set(significant_tokens(evidence))
    toks = significant_tokens(generated)
    if not toks:
        return 0.0
    overlap = sum(1 for t in toks if t in ev)
    return round(overlap / len(toks), 4)


def retrieval_relevance_score(question: str, hits: list[RetrievalHit]) -> float:
    """How much retrieved text lexically aligns with the question (top passages)."""
    if not hits:
        return 0.0
    # Weight early hits slightly more by taking first 5 concatenated.
    texts = [h.passage.text for h in hits[:5]]
    bundle = " ".join(texts)
    return lexical_support_ratio(question, bundle)


def chunk_coverage_score(hits: list[RetrievalHit], total_chunks: int) -> float:
    """Share of distinct transcript chunks touched by retrieval (0–1)."""
    if total_chunks <= 0 or not hits:
        return 0.0
    indices = {h.passage.chunk_index for h in hits}
    return round(min(1.0, len(indices) / total_chunks), 4)

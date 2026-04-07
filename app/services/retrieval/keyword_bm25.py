"""Lightweight BM25-style scoring over in-memory transcript chunks (pseudo-IDF on this video only)."""

from __future__ import annotations

import math
from collections import Counter

from app.models.qa_models import TranscriptChunkPassage


def tokenize(text: str) -> list[str]:
    return [
        t
        for t in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split()
        if t
    ]


def bm25_scores_normalized(
    question: str,
    passages: list[TranscriptChunkPassage],
    *,
    k1: float = 1.2,
    b: float = 0.75,
) -> dict[int, float]:
    """
    BM25 scores for each passage id, then divided by max so the best chunk is 1.0.

    IDF uses only the current transcript (per-video pseudo corpus), which is enough
    to reward rare query terms across chunks.
    """
    q_terms = list(dict.fromkeys(tokenize(question)))  # unique, order preserved
    n = len(passages)
    if n == 0 or not q_terms:
        return {}

    df: dict[str, int] = {}
    for term in q_terms:
        df[term] = sum(1 for p in passages if term in tokenize(p.text))

    idf: dict[str, float] = {}
    for term in q_terms:
        n_df = df.get(term, 0)
        idf[term] = math.log((n - n_df + 0.5) / (n_df + 0.5) + 1.0)

    doc_lengths: list[int] = []
    tfs: list[Counter[str]] = []
    for p in passages:
        toks = tokenize(p.text)
        doc_lengths.append(len(toks) if toks else 1)
        tfs.append(Counter(toks))

    avgdl = sum(doc_lengths) / n if n else 1.0

    raw: dict[int, float] = {}
    for idx, p in enumerate(passages):
        dl = doc_lengths[idx]
        tf = tfs[idx]
        score = 0.0
        for term in q_terms:
            f = float(tf.get(term, 0))
            denom = f + k1 * (1.0 - b + b * dl / avgdl)
            if denom <= 0:
                continue
            score += idf[term] * (f * (k1 + 1.0)) / denom
        raw[p.id] = score

    m = max(raw.values()) if raw else 0.0
    if m <= 0:
        return {pid: 0.0 for pid in raw}
    return {pid: v / m for pid, v in raw.items()}


def cosine_distance_to_similarity(cosine_distance: float) -> float:
    """Map pgvector cosine distance [0, 2] to a [0, 1] similarity (higher = closer)."""
    s = 1.0 - float(cosine_distance) / 2.0
    if s < 0.0:
        return 0.0
    if s > 1.0:
        return 1.0
    return s

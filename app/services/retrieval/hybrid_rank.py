"""Combine semantic and keyword scores into ranked :class:`RetrievalHit` rows."""

from __future__ import annotations

from app.models.qa_models import TranscriptChunkPassage
from app.models.retrieval_models import RetrievalHit
from app.services.retrieval.keyword_bm25 import bm25_scores_normalized, cosine_distance_to_similarity


def rank_hybrid(
    *,
    question: str,
    corpus: list[TranscriptChunkPassage],
    semantic_hits: list[tuple[TranscriptChunkPassage, float]],
    top_k: int,
    alpha: float,
    beta: float,
) -> list[RetrievalHit]:
    """
    ``semantic_hits`` are (passage, cosine_distance) from pgvector (lower distance = closer).

    Candidate pool = union of semantic hits and top keyword passages by BM25 (same pool cap).
    """
    if top_k <= 0 or not corpus:
        return []

    by_id: dict[int, TranscriptChunkPassage] = {p.id: p for p in corpus}
    kw = bm25_scores_normalized(question, corpus)

    pool_k = min(len(corpus), max(top_k * 5, 20))
    sem_by_id: dict[int, float] = {}
    for passage, dist in semantic_hits:
        sem_by_id[passage.id] = cosine_distance_to_similarity(dist)

    top_kw_ids = sorted(kw.keys(), key=lambda i: kw.get(i, 0.0), reverse=True)[:pool_k]
    candidate_ids = set(sem_by_id.keys()) | set(top_kw_ids)

    hits: list[RetrievalHit] = []
    for cid in candidate_ids:
        passage = by_id.get(cid)
        if passage is None:
            continue
        sem_s = sem_by_id.get(cid, 0.0)
        kw_s = kw.get(cid, 0.0)
        final = alpha * sem_s + beta * kw_s
        expl = (
            f"{alpha:g}×sem({sem_s:.2f})+{beta:g}×kw({kw_s:.2f})={final:.3f}"
        )
        hits.append(
            RetrievalHit(
                passage=passage,
                semantic_score=sem_s,
                keyword_score=kw_s,
                final_score=final,
                ranking_explanation=expl,
            )
        )

    hits.sort(key=lambda h: h.final_score, reverse=True)
    return hits[:top_k]

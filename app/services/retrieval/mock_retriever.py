from sqlalchemy.orm import Session

from app.config import Settings
from app.models.qa_models import TranscriptChunkPassage
from app.models.retrieval_models import RetrievalHit
from app.services.retrieval.base import ChunkRetriever
from app.services.retrieval.keyword_bm25 import bm25_scores_normalized, tokenize


class MockChunkRetriever(ChunkRetriever):
    """
    Keyword-only hybrid leg: BM25-style score over chunks (semantic leg is always 0 here).

    Final score: ``alpha * 0 + beta * keyword_score`` with scores in [0, 1].
    """

    def __init__(self, settings: Settings | None = None) -> None:
        from app.config import settings as default_settings

        self._settings = settings if settings is not None else default_settings

    def retrieve(
        self,
        question: str,
        passages: list[TranscriptChunkPassage],
        top_k: int,
        *,
        video_end_seconds: float | None = None,
        db: Session | None = None,
        video_id: str | None = None,
        language: str | None = None,
    ) -> list[RetrievalHit]:
        _ = video_end_seconds, db, video_id, language
        if not passages or top_k <= 0:
            return []

        alpha = self._settings.retrieval_hybrid_alpha
        beta = self._settings.retrieval_hybrid_beta

        if not tokenize(question):
            return [
                RetrievalHit(
                    passage=p,
                    semantic_score=0.0,
                    keyword_score=0.0,
                    final_score=0.0,
                    ranking_explanation="No query tokens; early chunks kept in order.",
                )
                for p in passages[:top_k]
            ]

        kw = bm25_scores_normalized(question, passages)
        hits: list[RetrievalHit] = []
        for p in passages:
            kw_s = kw.get(p.id, 0.0)
            sem_s = 0.0
            final = alpha * sem_s + beta * kw_s
            expl = f"{alpha:g}×sem(0.00)+{beta:g}×kw({kw_s:.2f})={final:.3f}"
            hits.append(
                RetrievalHit(
                    passage=p,
                    semantic_score=sem_s,
                    keyword_score=kw_s,
                    final_score=final,
                    ranking_explanation=expl,
                )
            )

        hits.sort(key=lambda h: h.final_score, reverse=True)
        return hits[:top_k]

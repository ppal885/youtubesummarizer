from sqlalchemy.orm import Session

from app.config import Settings
from app.exceptions import EmbeddingConfigurationError, EmbeddingInvocationError
from app.models.qa_models import TranscriptChunkPassage
from app.models.retrieval_models import RetrievalHit
from app.repositories.transcript_chunk_repository import TranscriptChunkRepository
from app.services.embeddings.factory import get_embedding_service
from app.services.retrieval.base import ChunkRetriever
from app.services.retrieval.hybrid_rank import rank_hybrid


class EmbeddingChunkRetriever(ChunkRetriever):
    """
    Hybrid retrieval: pgvector semantic candidates plus BM25-style keyword scores.

    ``final_score = alpha * semantic_score + beta * keyword_score`` (both [0, 1]).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._repo = TranscriptChunkRepository()
        self._provider = None

    def _provider_inst(self):
        if self._provider is None:
            self._provider = get_embedding_service(self._settings)
        return self._provider

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
        _ = video_end_seconds, passages
        if db is None or video_id is None or language is None:
            raise ValueError(
                "EmbeddingChunkRetriever requires keyword arguments db=, video_id=, and language=."
            )
        try:
            qvecs = self._provider_inst().embed([question])
        except EmbeddingConfigurationError:
            raise
        except EmbeddingInvocationError:
            raise
        except Exception as exc:
            raise EmbeddingInvocationError(f"Query embedding failed: {exc}") from exc
        if len(qvecs) != 1:
            raise EmbeddingInvocationError("Expected exactly one query embedding vector.")

        rows = self._repo.list_chunks(db, video_id, language)
        corpus = [TranscriptChunkPassage.model_validate(r) for r in rows]
        if not corpus:
            return []

        pool_k = min(len(corpus), max(top_k * 5, 20))
        semantic_hits = self._repo.search_similar_with_cosine_distance(
            db, video_id, language, qvecs[0], pool_k
        )

        return rank_hybrid(
            question=question,
            corpus=corpus,
            semantic_hits=semantic_hits,
            top_k=top_k,
            alpha=self._settings.retrieval_hybrid_alpha,
            beta=self._settings.retrieval_hybrid_beta,
        )

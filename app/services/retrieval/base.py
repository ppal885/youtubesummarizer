from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.models.qa_models import TranscriptChunkPassage
from app.models.retrieval_models import RetrievalHit


class ChunkRetriever(ABC):
    """Selects the most relevant transcript passages for a user question."""

    @abstractmethod
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
        """
        Return up to ``top_k`` hits ranked by hybrid or lexical scoring (best first).

        ``video_end_seconds`` bounds the last chunk's end time when persisting.
        ``db`` / ``video_id`` / ``language`` are required for pgvector + hybrid embedding path.
        """

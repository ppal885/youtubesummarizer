"""Typed models for transcript retrieval (embeddings + hybrid ranking)."""

from pydantic import BaseModel, Field

from app.models.qa_models import TranscriptChunkPassage


class TranscriptChunk(BaseModel):
    """One transcript slice with optional end time for grounding metadata."""

    chunk_id: int = Field(..., ge=0, description="Stable id, typically chunk_index.")
    text: str = Field(..., min_length=0)
    start_time: float = Field(..., ge=0, description="Start offset in seconds.")
    end_time: float | None = Field(
        default=None,
        ge=0,
        description="End offset in seconds when known (e.g. next chunk start or video end).",
    )


class EmbeddedChunk(BaseModel):
    """A transcript chunk paired with its embedding vector."""

    chunk: TranscriptChunk
    vector: list[float] = Field(..., min_length=1)


class RetrievalResult(BaseModel):
    """One retrieved passage with a similarity score (higher is better for cosine IP)."""

    passage: TranscriptChunkPassage
    score: float


class TranscriptRetrievalContext(BaseModel):
    """Optional context passed from Q&A into retrieval (e.g. for end_time on last chunk)."""

    video_end_seconds: float = Field(..., ge=0, description="End of playable/caption span in seconds.")


class RetrievalHit(BaseModel):
    """One ranked chunk after hybrid (semantic + keyword) scoring."""

    passage: TranscriptChunkPassage
    semantic_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Embedding similarity mapped to [0,1] (0 when unavailable).",
    )
    keyword_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="BM25-style score max-normalized over the transcript corpus.",
    )
    final_score: float = Field(
        ...,
        description="alpha * semantic_score + beta * keyword_score",
    )
    ranking_explanation: str = Field(
        ...,
        min_length=1,
        description="Human-readable breakdown of the combined score.",
    )

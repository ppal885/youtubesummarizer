from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.constants import VECTOR_STORAGE_DIMENSIONS
from app.db.embedding_vector import EmbeddingVector


class SummaryResult(Base):
    """Persisted summary row (production table name: ``summary_results``)."""

    __tablename__ = "summary_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String(32), index=True)
    source_url: Mapped[str] = mapped_column(String(2048))
    summary_type: Mapped[str] = mapped_column(String(32))
    language: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str] = mapped_column(Text)
    bullets_json: Mapped[str] = mapped_column(Text)
    suggested_questions_json: Mapped[str] = mapped_column(Text, default="[]")
    key_moments_json: Mapped[str] = mapped_column(Text, default="[]")
    transcript_length: Mapped[int] = mapped_column(Integer, default=0)
    chunks_processed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class SummaryJob(Base):
    """Persisted async summarize job state for background processing."""

    __tablename__ = "summary_jobs"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), index=True)
    video_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    source_url: Mapped[str] = mapped_column(String(2048))
    summary_type: Mapped[str] = mapped_column(String(32))
    language: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), index=True)
    error_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_result_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class LLMUsageRecord(Base):
    """Aggregated token/cost metrics for one API request using the LLM stack."""

    __tablename__ = "llm_usage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    video_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    endpoint: Mapped[str] = mapped_column(String(64), index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    llm_call_count: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimate_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class TranscriptChunkRecord(Base):
    """Transcript slices for Q&A with optional dense embeddings (pgvector on PostgreSQL)."""

    __tablename__ = "transcript_chunks"
    __table_args__ = (
        UniqueConstraint(
            "video_id",
            "language",
            "chunk_index",
            name="uq_transcript_chunk_video_lang_idx",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String(32), index=True)
    language: Mapped[str] = mapped_column(String(16), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, index=True)
    text: Mapped[str] = mapped_column(Text)
    start_time: Mapped[float] = mapped_column("start_time", Float)
    end_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        EmbeddingVector(VECTOR_STORAGE_DIMENSIONS),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    @hybrid_property
    def start_seconds(self) -> float:  # noqa: D401
        """Alias for Pydantic ``TranscriptChunkPassage`` (caption start in seconds)."""
        return self.start_time

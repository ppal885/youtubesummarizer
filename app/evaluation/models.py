"""Typed evaluation payloads (summary faithfulness, Q&A grounding, retrieval, latency)."""

from pydantic import BaseModel, Field


class SummaryEvaluationResult(BaseModel):
    """Metrics for one summarization pass (brief pipeline)."""

    latency_ms: float = Field(..., ge=0, description="Wall time for summarize_from_url.")
    summary_faithfulness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Lexical support: fraction of summary+bullet tokens found in full transcript.",
    )
    chunks_processed: int = Field(..., ge=0)
    transcript_length: int = Field(..., ge=0)


class QuestionEvaluationResult(BaseModel):
    """Per-question Q&A metrics after one copilot graph run."""

    question: str = Field(..., min_length=1)
    latency_ms: float = Field(..., ge=0, description="End-to-end ask graph wall time.")
    retrieved_chunk_count: int = Field(
        ...,
        ge=0,
        description="Hits returned by retrieval (before citation trim to sources).",
    )
    citation_source_count: int = Field(
        ...,
        ge=0,
        description="Sources attached to the API response (≤3).",
    )
    answer_has_sources: bool = Field(
        ...,
        description="True when at least one citation source was returned.",
    )
    answer_grounding_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Verifier confidence (lexical grounding) from the copilot pipeline.",
    )
    retrieval_relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Lexical overlap between the question and retrieved passage text.",
    )
    chunk_coverage_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Unique chunk indices in retrieval / total transcript chunks.",
    )
    answer_excerpt: str = Field(
        default="",
        max_length=400,
        description="Short preview of final answer for logs (not full text).",
    )


class EvaluationAggregateMetrics(BaseModel):
    """Run-level rollups for dashboards or CI summaries."""

    average_latency_ms: float = Field(
        ...,
        ge=0.0,
        description="Mean latency over 1 summarize + N question runs.",
    )
    mean_answer_grounding_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Mean verifier confidence; None when no questions were evaluated.",
    )
    mean_retrieval_relevance: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Mean retrieval_relevance_score across questions.",
    )
    mean_chunk_coverage: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Mean chunk_coverage_score across questions.",
    )
    summary_faithfulness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Same as summary.summary_faithfulness_score (run-level headline).",
    )


class VideoEvaluationRun(BaseModel):
    """Full evaluation for one video URL and a list of questions."""

    video_url: str
    video_id: str
    language: str
    transcript_char_count: int = Field(..., ge=0)
    total_transcript_chunks: int = Field(..., ge=0)
    summary: SummaryEvaluationResult
    questions: list[QuestionEvaluationResult] = Field(default_factory=list)
    aggregate: EvaluationAggregateMetrics

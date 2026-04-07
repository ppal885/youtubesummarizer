from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.request_models import LearningLevel


class KeyMoment(BaseModel):
    time: str = Field(..., description="Formatted timestamp (mm:ss or hh:mm:ss)")
    note: str = Field(..., min_length=0)


class VideoChapter(BaseModel):
    """A logical section of the video inferred from transcript topic continuity."""

    title: str = Field(..., min_length=1, description="Short heading grounded in this segment.")
    start_time: float = Field(..., ge=0, description="Chapter start in seconds from video start.")
    formatted_time: str = Field(..., description="Same instant as start_time (mm:ss or hh:mm:ss).")
    short_summary: str = Field(
        ...,
        min_length=0,
        max_length=800,
        description="Brief description of this segment; must reflect transcript content only.",
    )


class DeveloperStudyDigest(BaseModel):
    """Developer-mode extraction: concepts, tooling, patterns, and optional pseudo-code — transcript-grounded only."""

    concepts: list[str] = Field(
        default_factory=list,
        description="Key technical ideas or terms the speaker explains or relies on.",
    )
    tools: list[str] = Field(
        default_factory=list,
        description="Tools, frameworks, libraries, CLIs, or services explicitly named.",
    )
    patterns: list[str] = Field(
        default_factory=list,
        description="Code or architecture patterns (e.g. MVC, retry, caching) discussed in the captions.",
    )
    best_practices: list[str] = Field(
        default_factory=list,
        description="Recommendations or habits the speaker presents as good practice.",
    )
    pitfalls: list[str] = Field(
        default_factory=list,
        description="Mistakes, footguns, anti-patterns, or warnings mentioned.",
    )
    pseudo_code: str = Field(
        default="",
        description="Plain-language or simplified pseudo-code when the talk is code-related; otherwise empty.",
    )
    explanation: str = Field(
        default="",
        description="Step-by-step logic narrative; highlight APIs, flags, or calls the transcript specifies.",
    )


class FinalSummary(BaseModel):
    video_id: str
    title: str
    summary: str
    bullets: list[str]
    key_moments: list[KeyMoment]
    transcript_length: int = Field(..., ge=0)
    chunks_processed: int = Field(..., ge=0)
    learning_level: LearningLevel = Field(
        default="intermediate",
        description="Learning mode used when generating this summary.",
    )
    suggested_questions: list[str] = Field(
        default_factory=list,
        description="5–8 follow-up questions generated from the transcript (LLM).",
    )
    chapters: list[VideoChapter] = Field(
        default_factory=list,
        description="Topic-based sections from transcript (fewer entries when segmentation is uncertain).",
    )
    developer_digest: DeveloperStudyDigest | None = Field(
        default=None,
        description="Structured developer-oriented notes when summarization used developer_mode.",
    )


SummaryJobState = Literal["queued", "running", "completed", "failed"]


class SummaryJobAcceptedResponse(BaseModel):
    job_id: str
    status: SummaryJobState
    status_url: str


class SummaryJobError(BaseModel):
    stage: str | None = None
    type: str
    detail: str


class SummaryJobStatusResponse(BaseModel):
    job_id: str
    status: SummaryJobState
    source_url: str
    summary_type: str
    language: str
    video_id: str | None = None
    summary_result_id: int | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: FinalSummary | None = None
    error: SummaryJobError | None = None


class CompareVideosResponse(BaseModel):
    """Structured comparison of two transcript-derived summaries."""

    summary_1: str = Field(..., description="Prose summary for video 1")
    summary_2: str = Field(..., description="Prose summary for video 2")
    similarities: list[str] = Field(
        default_factory=list,
        description="Overlapping themes or claims (LLM, grounded in supplied summaries).",
    )
    differences: list[str] = Field(
        default_factory=list,
        description="Contrasts between the two videos (LLM, grounded in supplied summaries).",
    )


class SynthesizeResponse(BaseModel):
    """Multi-video knowledge synthesis for a topic (each video summarized first, then LLM merge)."""

    combined_summary: str = Field(..., description="Merged overview across videos on the topic.")
    common_ideas: list[str] = Field(
        default_factory=list,
        description="Shared themes or claims appearing across the set.",
    )
    differences: list[str] = Field(
        default_factory=list,
        description="How videos diverge in focus, depth, or conclusions.",
    )
    best_explanation: str = Field(
        ...,
        description="Clearest take on the topic with attribution to specific videos when applicable.",
    )


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class PublicLlmConfig(BaseModel):
    """Non-secret LLM settings for UI and ops (no API keys)."""

    provider: str = Field(..., description="mock, openai, or anthropic")
    model: str
    configured: bool = Field(
        ...,
        description="True if this provider has the credentials it needs to call a real model.",
    )
    base_url_custom: bool = Field(
        ...,
        description="True when LLM_BASE_URL is set (OpenAI-compatible custom endpoint).",
    )
    json_response_format: bool = Field(
        ...,
        description="Whether OpenAI-compatible provider requests json_object mode.",
    )


class PublicConfigResponse(BaseModel):
    """Safe configuration snapshot for the UI."""

    app_name: str
    app_version: str
    llm: PublicLlmConfig
    demo_mode: bool = Field(
        default=False,
        description="If true, backend serves preloaded summary/Q&A for demo_sample_video_url.",
    )
    demo_sample_video_url: str | None = Field(
        default=None,
        description="Canonical watch URL for offline demo content when demo_mode is on.",
    )


class RootResponse(BaseModel):
    message: str
    version: str
    docs: str


class StoredSummaryListItem(BaseModel):
    """Subset of a persisted summary for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: str
    source_url: str
    summary_type: str
    language: str
    title: str
    transcript_length: int
    chunks_processed: int
    created_at: datetime


class AskCitationSource(BaseModel):
    """One retrieved transcript excerpt cited for the answer."""

    start_time: float = Field(..., ge=0, description="Chunk start offset in seconds")
    formatted_time: str = Field(..., description="Same instant as start_time (mm:ss or hh:mm:ss)")
    text: str = Field(..., description="Transcript excerpt (truncated for the response)")


class AskResponse(BaseModel):
    answer: str
    sources: list[AskCitationSource]
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="0 when unsupported or refusal; higher when lexical grounding to sources is strong.",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Raw overlap score between the answer and retrieved transcript chunks.",
    )


class QAResponse(BaseModel):
    """Structured transcript-grounded answer emitted by the LLM service."""

    answer: str = Field(
        default="Not mentioned in video",
        description='Answer using ONLY provided context; if unsupported, exactly "Not mentioned in video".',
    )


class GlossaryTerm(BaseModel):
    term: str = Field(..., min_length=1)
    definition: str = Field(..., min_length=0)


class NotesResponse(BaseModel):
    video_id: str
    title: str
    concise_notes: str = Field(..., description="Short review notes grounded in the transcript.")
    detailed_notes: str = Field(..., description="Expanded notes grounded in the transcript.")
    glossary_terms: list[GlossaryTerm] = Field(
        default_factory=list,
        description="Terms with definitions from transcript content.",
    )


class QuizQuestionItem(BaseModel):
    question: str
    options: list[str] = Field(..., min_length=4, max_length=4)
    answer: str = Field(..., description="Correct option text (one of options).")
    explanation: str


class QuizResponse(BaseModel):
    video_id: str
    title: str
    questions: list[QuizQuestionItem] = Field(default_factory=list)


class FlashcardItem(BaseModel):
    front: str
    back: str
    timestamp_seconds: float | None = Field(
        default=None,
        description="Optional jump time in the video when grounded to a caption chunk.",
    )
    formatted_time: str | None = Field(
        default=None,
        description="Human-readable time matching timestamp_seconds when set.",
    )


class FlashcardsResponse(BaseModel):
    video_id: str
    title: str
    cards: list[FlashcardItem] = Field(default_factory=list)


class InterviewPrepQaItem(BaseModel):
    question: str = Field(..., description="Interview-style question grounded in the video.")
    answer: str = Field(..., description="Concise answer grounded in the transcript.")


class InterviewPrepSystemDesignInsight(BaseModel):
    title: str = Field(..., description="Short label for a design or architecture angle from the talk.")
    insight: str = Field(..., description="Tradeoff, pattern, or constraint tied to transcript content.")


class InterviewPrepEdgeCase(BaseModel):
    scenario: str = Field(..., description="Edge case or sharp question.")
    discussion: str = Field(..., description="Reasoning or clarification grounded in what was discussed.")


class InterviewPrepResponse(BaseModel):
    """Developer interview preparation derived from the transcript."""

    video_id: str
    title: str
    key_questions: list[InterviewPrepQaItem] = Field(
        default_factory=list,
        description="Q&A pairs for interview practice.",
    )
    system_design_insights: list[InterviewPrepSystemDesignInsight] = Field(
        default_factory=list,
        description="Design and systems thinking angles supported by the video.",
    )
    edge_cases: list[InterviewPrepEdgeCase] = Field(
        default_factory=list,
        description="Failure modes, boundaries, and follow-up probes.",
    )


class ExportNotesResponse(BaseModel):
    """Markdown bundle from ``POST /api/v1/export-notes``."""

    markdown_content: str = Field(..., description="Full markdown document (sections: Title … Quiz).")
    suggested_filename: str = Field(
        ...,
        description="Safe suggested download name ending in .md (slug + video id).",
    )

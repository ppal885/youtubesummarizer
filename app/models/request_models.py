from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


SummaryType = Literal["brief", "detailed", "bullet", "technical"]

LearningLevel = Literal["beginner", "intermediate", "advanced"]


class SummarizeRequest(BaseModel):
    url: HttpUrl = Field(..., description="YouTube video URL")
    summary_type: SummaryType = Field(default="brief")
    language: str = Field(default="en", min_length=2, max_length=10)
    learning_level: LearningLevel = Field(
        default="intermediate",
        description="Controls explanation depth and tone; all content stays transcript-grounded.",
    )
    developer_mode: bool = Field(
        default=False,
        description="When true, adds a transcript-grounded developer digest (concepts, tools, patterns, etc.).",
    )


class CompareRequest(BaseModel):
    """Body for POST /api/v1/compare — two videos summarized then contrasted via LLM."""

    url_1: HttpUrl = Field(..., description="First YouTube video URL")
    url_2: HttpUrl = Field(..., description="Second YouTube video URL")
    summary_type: SummaryType = Field(
        default="brief",
        description="Passed through to the summarization pipeline for both videos.",
    )
    language: str = Field(default="en", min_length=2, max_length=10)


class SynthesizeRequest(BaseModel):
    """Body for POST /api/v1/synthesize — summarize each video, then merge through the LLM on a topic."""

    urls: list[HttpUrl] = Field(
        ...,
        min_length=2,
        max_length=6,
        description="YouTube watch URLs (2–6). Duplicate video ids are de-duplicated while preserving order.",
    )
    topic: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Lens for synthesis (e.g. 'caching strategies', 'career advice for juniors').",
    )
    summary_type: SummaryType = Field(
        default="brief",
        description="Summarization style applied to every video before merging.",
    )
    language: str = Field(default="en", min_length=2, max_length=10)


class TranscriptLearningRequest(BaseModel):
    """Body for study endpoints: notes, quiz, flashcards, interview prep (transcript-grounded)."""

    url: HttpUrl = Field(..., description="YouTube video URL")
    language: str = Field(
        default="en",
        min_length=2,
        max_length=10,
        description="Transcript language code (optional; default en).",
    )


ExportNotesType = Literal["markdown"]


class ExportNotesRequest(BaseModel):
    """Body for POST /api/v1/export-notes — bundled markdown from summary + learning artifacts."""

    url: HttpUrl = Field(..., description="YouTube video URL")
    export_type: ExportNotesType = Field(
        default="markdown",
        description="Export format; only markdown is supported today.",
    )
    language: str = Field(
        default="en",
        min_length=2,
        max_length=10,
        description="Caption language for transcript fetch (same as summarize / learning).",
    )


class AskRequest(BaseModel):
    """Body for POST /api/v1/ask. Only ``url`` and ``question`` are required; ``language`` selects caption track."""

    url: HttpUrl = Field(..., description="YouTube video URL")
    question: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(
        default="en",
        min_length=2,
        max_length=10,
        description="Transcript language code (optional; default en).",
    )

"""Pydantic shapes for JSON emitted by LLM providers (OpenAI `json_object` mode)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.response_models import QAResponse
from app.models.summary_models import ChunkSummary


class StructuredSummaryPayload(BaseModel):
    """JSON object the model must return: plain strings only, no nested prose."""

    summary: str = Field(..., description="Concise prose grounded only in the input.")
    bullets: list[str] = Field(
        default_factory=list,
        description="Short bullet points; each must restate ideas present in the input.",
    )

    def to_chunk_summary(self) -> ChunkSummary:
        return ChunkSummary(summary=self.summary, bullets=self.bullets)


class QaAnswerPayload(QAResponse):
    """JSON object returned by the model for transcript Q&A."""

    answer: str = Field(
        default="Not mentioned in video",
        description='Answer using ONLY provided context; if unsupported, exactly "Not mentioned in video".',
    )


QueryUnderstandingIntent = Literal["factual", "conceptual", "comparison", "definition"]


class QaQueryUnderstandingPayload(BaseModel):
    """Structured query understanding for transcript Q&A retrieval (original question stays for answering)."""

    intent: QueryUnderstandingIntent = Field(
        ...,
        description="factual: specific fact/timing/claim; conceptual: why/how/motivation; "
        "comparison: A vs B; definition: what is / meaning of term.",
    )
    normalized_query: str = Field(
        ...,
        description="Search-oriented rewrite: clear, keyword-rich phrasing grounded in the user's wording only.",
    )
    expansion_keywords: list[str] = Field(
        default_factory=list,
        description="Extra salient tokens or short phrases (synonyms, entities) implied by the question; max ~12.",
    )


class CompressedQaContextItemPayload(BaseModel):
    """One row of RAG context after LLM compression."""

    summary: str = Field(
        ...,
        min_length=1,
        description="Dense recap using only facts from the cited chunk excerpts.",
    )
    source_chunk_indices: list[int] = Field(
        ...,
        min_length=1,
        description="chunk_index values from the provided RETRIEVAL blocks (must exist in input).",
    )
    time_start_seconds: float = Field(..., ge=0, description="Start time for this row (usually earliest cited chunk).")
    time_end_seconds: float | None = Field(
        default=None,
        ge=0,
        description="Optional end time when spanning multiple chunks.",
    )


class CompressedQaContextPayload(BaseModel):
    """JSON object: compressed CONTEXT rows for Q&A (3–5 items enforced downstream)."""

    items: list[CompressedQaContextItemPayload] = Field(
        ...,
        min_length=1,
        max_length=6,
    )


class SuggestedQuestionsPayload(BaseModel):
    """JSON object: ``questions`` array from the model (normalized to 5–8 items downstream)."""

    questions: list[str] = Field(
        default_factory=list,
        description="Candidate viewer questions grounded in the transcript.",
    )


class VideoPairComparePayload(BaseModel):
    """JSON object from the model comparing two video summaries."""

    similarities: list[str] = Field(
        default_factory=list,
        description="Shared themes or overlaps grounded in both inputs.",
    )
    differences: list[str] = Field(
        default_factory=list,
        description="Contrasts grounded in the two inputs.",
    )


class MultiVideoSynthesisPayload(BaseModel):
    """JSON object merging several transcript-derived summaries under a user topic."""

    combined_summary: str = Field(
        ...,
        description="Unified narrative across videos, focused on the topic; only facts from supplied summaries/bullets.",
    )
    common_ideas: list[str] = Field(
        default_factory=list,
        description="Themes, claims, or methods that align across two or more videos.",
    )
    differences: list[str] = Field(
        default_factory=list,
        description="Contrasts in emphasis, depth, audience, conclusions, or scope between videos.",
    )
    best_explanation: str = Field(
        ...,
        description="Clearest explanation for the topic from the set: cite which video title(s) carry it, or synthesize explicitly from their text only.",
    )


class GlossaryTermPayload(BaseModel):
    term: str = Field(..., min_length=1, description="Term as used in the transcript.")
    definition: str = Field(
        ...,
        min_length=0,
        description="Short definition; must paraphrase transcript content only.",
    )


class LearningNotesPayload(BaseModel):
    """JSON shape for POST /api/v1/notes (learning assistant)."""

    concise_notes: str = Field(
        ...,
        description="Short study sheet: key ideas only, grounded in the transcript.",
    )
    detailed_notes: str = Field(
        ...,
        description="Expanded notes with structure (paragraphs or bullet-style lines in one string).",
    )
    glossary_terms: list[GlossaryTermPayload] = Field(
        default_factory=list,
        description="Important terms with definitions from the transcript.",
    )


class QuizQuestionPayload(BaseModel):
    question: str
    options: list[str] = Field(
        default_factory=list,
        description="Multiple-choice options; service keeps items with exactly four options.",
    )
    correct_index: int = Field(
        default=0,
        description="0-based index into options; must be 0–3 when there are four options.",
    )
    explanation: str = ""


class QuizPayload(BaseModel):
    questions: list[QuizQuestionPayload] = Field(default_factory=list)


class FlashcardItemPayload(BaseModel):
    front: str
    back: str
    timestamp_seconds: float | None = Field(
        default=None,
        description="Optional video offset in seconds when the idea appears; must match a labeled timestamp.",
    )


class FlashcardsPayload(BaseModel):
    cards: list[FlashcardItemPayload] = Field(default_factory=list)


class InterviewPrepQaPairPayload(BaseModel):
    question: str = Field(
        ...,
        description="Technical or behavioral interview question a hiring panel might ask about this content.",
    )
    answer: str = Field(
        ...,
        description="Concise interview-style answer; paraphrase only facts supported by the transcript.",
    )


class InterviewPrepSystemDesignInsightPayload(BaseModel):
    title: str = Field(..., min_length=1, description="Short heading (e.g. scaling, storage, consistency).")
    insight: str = Field(
        ...,
        description="Design tradeoff, pattern, or constraint tied to what the speaker actually discussed.",
    )


class InterviewPrepEdgeCasePayload(BaseModel):
    scenario: str = Field(..., description="Edge case, failure mode, or sharp boundary question.")
    discussion: str = Field(
        ...,
        description="How to reason through it or what to watch for; stay grounded in the transcript.",
    )


class InterviewPrepPayload(BaseModel):
    """JSON shape for developer interview prep from a video transcript."""

    key_questions: list[InterviewPrepQaPairPayload] = Field(
        default_factory=list,
        description="6–10 pairs when the transcript supports it; fewer if the video is very short.",
    )
    system_design_insights: list[InterviewPrepSystemDesignInsightPayload] = Field(
        default_factory=list,
        description="Architecture, reliability, data modeling, or ops angles explicitly supported by the talk.",
    )
    edge_cases: list[InterviewPrepEdgeCasePayload] = Field(
        default_factory=list,
        description="Bottlenecks, race conditions, partial failure, ambiguity, or 'what if' probes grounded in content.",
    )


class ChapterLlmItem(BaseModel):
    """One chapter label from the model; order aligns with supplied timed segments."""

    title: str = Field(..., min_length=1, description="Concise title from the segment text only.")
    short_summary: str = Field(
        ...,
        min_length=0,
        description="1–3 sentences; only facts present in that segment.",
    )


class ChaptersLlmPayload(BaseModel):
    chapters: list[ChapterLlmItem] = Field(
        ...,
        description="Same length and order as the timed segments in the user message.",
    )

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.models.chapter_models import ChapterSegment
from app.models.qa_models import TranscriptChunkPassage
from app.models.response_models import DeveloperStudyDigest, QAResponse
from app.models.retrieval_models import RetrievalHit
from app.models.summary_models import ChunkSummary
from app.services.llm.schemas import (
    ChapterLlmItem,
    CompressedQaContextPayload,
    FlashcardsPayload,
    InterviewPrepPayload,
    LearningNotesPayload,
    MultiVideoSynthesisPayload,
    QaQueryUnderstandingPayload,
    QuizPayload,
    VideoPairComparePayload,
)


class LLMService(ABC):
    @abstractmethod
    async def summarize_chunk(
        self,
        chunk: str,
        summary_type: str,
        *,
        learning_level: str = "intermediate",
    ) -> ChunkSummary:
        """Summarize a single transcript chunk."""

    @abstractmethod
    async def merge_summaries(
        self,
        chunk_summaries: list[ChunkSummary],
        summary_type: str,
        *,
        learning_level: str = "intermediate",
    ) -> ChunkSummary:
        """Combine per-chunk summaries into one cohesive summary."""

    @abstractmethod
    async def answer_question(
        self,
        question: str,
        context_passages: list[TranscriptChunkPassage],
        *,
        orientation_notes: str | None = None,
        evidence_synthesis_notes: str | None = None,
    ) -> QAResponse:
        """Answer ``question`` using only ``context_passages`` (plain text).

        ``orientation_notes`` is optional non-evidence context (e.g. coarse themes);
        ``evidence_synthesis_notes`` guides multi-segment synthesis (also non-evidence instructions);
        the model must still ground claims only in ``context_passages``.
        """

    @abstractmethod
    async def answer_question_stream(
        self,
        question: str,
        context_passages: list[TranscriptChunkPassage],
        *,
        orientation_notes: str | None = None,
        evidence_synthesis_notes: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream answer fragments (plain text); same grounding contract as ``answer_question``."""

    @abstractmethod
    async def compress_qa_retrieval_context(
        self,
        question: str,
        hits: list[RetrievalHit],
        target_count: int,
    ) -> CompressedQaContextPayload:
        """Return ``target_count`` compressed context rows (JSON contract) from ranked retrieval hits."""

    @abstractmethod
    async def generate_suggested_questions(self, transcript: str) -> list[str]:
        """Return 5–8 natural follow-up questions grounded in the full transcript text."""

    @abstractmethod
    async def generate_chapters(self, segments: list[ChapterSegment]) -> list[ChapterLlmItem]:
        """Return one title and short summary per timed segment (same order and length)."""

    @abstractmethod
    async def compare_two_video_summaries(
        self,
        *,
        title_1: str,
        summary_1: str,
        bullets_1: list[str],
        title_2: str,
        summary_2: str,
        bullets_2: list[str],
    ) -> VideoPairComparePayload:
        """Return similarities and differences grounded only in the supplied summary material."""

    @abstractmethod
    async def synthesize_multi_video_summaries(self, user_message: str) -> MultiVideoSynthesisPayload:
        """Return structured multi-video synthesis from the built user message (topic + per-video summaries)."""

    @abstractmethod
    async def generate_study_notes(self, user_message: str) -> LearningNotesPayload:
        """Return structured study notes; ``user_message`` is the full user prompt (often labeled transcript)."""

    @abstractmethod
    async def generate_quiz(self, user_message: str) -> QuizPayload:
        """Return multiple-choice questions from the supplied user prompt text."""

    @abstractmethod
    async def generate_flashcards(self, user_message: str) -> FlashcardsPayload:
        """Return flashcards from the supplied user prompt text."""

    @abstractmethod
    async def generate_interview_prep(self, user_message: str) -> InterviewPrepPayload:
        """Return structured developer interview prep from labeled transcript user message."""

    @abstractmethod
    async def generate_developer_study_digest(self, user_message: str) -> DeveloperStudyDigest:
        """Return developer-mode extraction; ``user_message`` is labeled transcript text (see learning prompts)."""

    @abstractmethod
    async def understand_qa_query(self, question: str) -> QaQueryUnderstandingPayload:
        """Classify the viewer question and emit a retrieval-oriented rewrite (original question is still used to answer)."""

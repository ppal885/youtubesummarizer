import json
from collections.abc import AsyncIterator
from typing import Any, TypeVar

from anthropic import AnthropicError, AsyncAnthropic
from pydantic import BaseModel

from app.config import Settings
from app.models.chapter_models import ChapterSegment
from app.models.qa_models import TranscriptChunkPassage
from app.models.response_models import DeveloperStudyDigest, QAResponse
from app.models.retrieval_models import RetrievalHit
from app.models.summary_models import ChunkSummary
from app.services.llm.base import LLMService
from app.services.llm.chapter_prompting import CHAPTERS_SYSTEM, build_chapters_user_message
from app.services.llm.compare_prompting import COMPARE_TWO_VIDEOS_SYSTEM, build_compare_user_message
from app.services.llm.context_compression_prompting import (
    COMPRESS_QA_CONTEXT_SYSTEM,
    build_compress_qa_user_message,
)
from app.services.llm.developer_mode_prompting import DEVELOPER_MODE_SYSTEM
from app.services.llm.learning_prompting import (
    FLASHCARDS_SYSTEM,
    INTERVIEW_PREP_SYSTEM,
    QUIZ_SYSTEM,
    STUDY_NOTES_SYSTEM,
)
from app.services.llm.prompting import SYSTEM_INSTRUCTIONS, chunk_user_message, merge_user_message
from app.services.llm.provider_support import LoggedLLMProviderMixin
from app.services.llm.qa_prompting import QA_STREAM_SYSTEM_INSTRUCTIONS, QA_SYSTEM_INSTRUCTIONS
from app.services.llm.qa_query_understanding_prompting import QA_QUERY_UNDERSTANDING_SYSTEM
from app.services.llm.qa_user_message import build_qa_user_prompt
from app.services.llm.schemas import (
    ChapterLlmItem,
    ChaptersLlmPayload,
    CompressedQaContextPayload,
    FlashcardsPayload,
    InterviewPrepPayload,
    LearningNotesPayload,
    MultiVideoSynthesisPayload,
    QaAnswerPayload,
    QaQueryUnderstandingPayload,
    QuizPayload,
    StructuredSummaryPayload,
    SuggestedQuestionsPayload,
    VideoPairComparePayload,
)
from app.services.llm.suggested_questions_normalize import normalize_suggested_questions
from app.services.llm.suggested_questions_prompting import SUGGESTED_QUESTIONS_SYSTEM
from app.services.llm.synthesize_prompting import MULTI_VIDEO_SYNTHESIS_SYSTEM
from app.services.llm.token_usage import extract_anthropic_token_usage

_LearnT = TypeVar("_LearnT", bound=BaseModel)


class AnthropicLLMService(LoggedLLMProviderMixin, LLMService):
    """Claude Messages API with structured JSON payloads parsed from assistant text."""

    _provider_name = "anthropic"

    def __init__(self, settings: Settings) -> None:
        self._model = settings.llm_model
        self._temperature = 0.25
        self._suggested_questions_temperature = 0.35
        self._compare_temperature = 0.3
        self._learning_temperature = 0.35
        self._chapters_temperature = 0.3
        self._max_tokens = 8192
        self._client = AsyncAnthropic(
            api_key=settings.llm_api_key.strip(),
            timeout=settings.llm_timeout_seconds,
        )

    async def summarize_chunk(
        self,
        chunk: str,
        summary_type: str,
        *,
        learning_level: str = "intermediate",
    ) -> ChunkSummary:
        payload = await self._structured_completion(
            "summarize_chunk",
            SYSTEM_INSTRUCTIONS,
            chunk_user_message(chunk, summary_type, learning_level),
            StructuredSummaryPayload,
            temperature=self._temperature,
        )
        return payload.to_chunk_summary()

    async def merge_summaries(
        self,
        chunk_summaries: list[ChunkSummary],
        summary_type: str,
        *,
        learning_level: str = "intermediate",
    ) -> ChunkSummary:
        if not chunk_summaries:
            return ChunkSummary(summary="", bullets=[])

        serialized: list[dict[str, Any]] = [
            {"summary": item.summary, "bullets": item.bullets} for item in chunk_summaries
        ]
        payload = await self._structured_completion(
            "merge_summaries",
            SYSTEM_INSTRUCTIONS,
            merge_user_message(
                json.dumps(serialized, ensure_ascii=False),
                summary_type,
                learning_level,
            ),
            StructuredSummaryPayload,
            temperature=self._temperature,
        )
        return payload.to_chunk_summary()

    async def answer_question(
        self,
        question: str,
        context_passages: list[TranscriptChunkPassage],
        *,
        orientation_notes: str | None = None,
        evidence_synthesis_notes: str | None = None,
    ) -> QAResponse:
        if not context_passages:
            return QAResponse(
                answer="Not found in context: no transcript passages were retrieved for this question."
            )
        payload = await self._structured_completion(
            "answer_question",
            QA_SYSTEM_INSTRUCTIONS,
            build_qa_user_prompt(
                question,
                context_passages,
                orientation_notes=orientation_notes,
                evidence_synthesis_notes=evidence_synthesis_notes,
            ),
            QaAnswerPayload,
            temperature=self._temperature,
        )
        return QAResponse(answer=payload.answer.strip())

    async def answer_question_stream(
        self,
        question: str,
        context_passages: list[TranscriptChunkPassage],
        *,
        orientation_notes: str | None = None,
        evidence_synthesis_notes: str | None = None,
    ) -> AsyncIterator[str]:
        if not context_passages:
            yield "Not found in context: no transcript passages were retrieved for this question."
            return
        async for fragment in self._stream_completion(
            "answer_question_stream",
            QA_STREAM_SYSTEM_INSTRUCTIONS,
            build_qa_user_prompt(
                question,
                context_passages,
                orientation_notes=orientation_notes,
                evidence_synthesis_notes=evidence_synthesis_notes,
            ),
            temperature=self._temperature,
        ):
            yield fragment

    async def compress_qa_retrieval_context(
        self,
        question: str,
        hits: list[RetrievalHit],
        target_count: int,
    ) -> CompressedQaContextPayload:
        return await self._structured_completion(
            "compress_qa_retrieval_context",
            COMPRESS_QA_CONTEXT_SYSTEM,
            build_compress_qa_user_message(question, hits, target_count),
            CompressedQaContextPayload,
            temperature=self._temperature,
        )

    async def generate_suggested_questions(self, transcript: str) -> list[str]:
        payload = await self._structured_completion(
            "generate_suggested_questions",
            SUGGESTED_QUESTIONS_SYSTEM,
            f"TRANSCRIPT:\n{transcript.strip()}\n",
            SuggestedQuestionsPayload,
            temperature=self._suggested_questions_temperature,
        )
        return normalize_suggested_questions(payload.questions)

    async def generate_chapters(self, segments: list[ChapterSegment]) -> list[ChapterLlmItem]:
        if not segments:
            return []
        payload = await self._structured_completion(
            "generate_chapters",
            CHAPTERS_SYSTEM,
            build_chapters_user_message(segments),
            ChaptersLlmPayload,
            temperature=self._chapters_temperature,
        )
        return list(payload.chapters)

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
        return await self._structured_completion(
            "compare_two_video_summaries",
            COMPARE_TWO_VIDEOS_SYSTEM,
            build_compare_user_message(
                title_1=title_1,
                summary_1=summary_1,
                bullets_1=bullets_1,
                title_2=title_2,
                summary_2=summary_2,
                bullets_2=bullets_2,
            ),
            VideoPairComparePayload,
            temperature=self._compare_temperature,
        )

    async def synthesize_multi_video_summaries(self, user_message: str) -> MultiVideoSynthesisPayload:
        return await self._structured_completion(
            "synthesize_multi_video_summaries",
            MULTI_VIDEO_SYNTHESIS_SYSTEM,
            user_message,
            MultiVideoSynthesisPayload,
            temperature=self._compare_temperature,
        )

    async def generate_study_notes(self, user_message: str) -> LearningNotesPayload:
        return await self._learning_completion(
            "generate_study_notes", STUDY_NOTES_SYSTEM, user_message, LearningNotesPayload
        )

    async def generate_quiz(self, user_message: str) -> QuizPayload:
        return await self._learning_completion("generate_quiz", QUIZ_SYSTEM, user_message, QuizPayload)

    async def generate_flashcards(self, user_message: str) -> FlashcardsPayload:
        return await self._learning_completion("generate_flashcards", FLASHCARDS_SYSTEM, user_message, FlashcardsPayload)

    async def generate_interview_prep(self, user_message: str) -> InterviewPrepPayload:
        return await self._learning_completion(
            "generate_interview_prep",
            INTERVIEW_PREP_SYSTEM,
            user_message,
            InterviewPrepPayload,
        )

    async def generate_developer_study_digest(self, user_message: str) -> DeveloperStudyDigest:
        return await self._learning_completion(
            "generate_developer_study_digest",
            DEVELOPER_MODE_SYSTEM,
            user_message,
            DeveloperStudyDigest,
        )

    async def understand_qa_query(self, question: str) -> QaQueryUnderstandingPayload:
        return await self._learning_completion(
            "understand_qa_query",
            QA_QUERY_UNDERSTANDING_SYSTEM,
            f"VIEWER_QUESTION:\n{question.strip()}\n",
            QaQueryUnderstandingPayload,
        )

    async def _learning_completion(
        self,
        capability: str,
        system_prompt: str,
        user_message: str,
        payload_model: type[_LearnT],
    ) -> _LearnT:
        return await self._structured_completion(
            capability,
            system_prompt,
            user_message,
            payload_model,
            temperature=self._learning_temperature,
        )

    async def _structured_completion(
        self,
        capability: str,
        system_prompt: str,
        user_message: str,
        payload_model: type[_LearnT],
        *,
        temperature: float,
    ) -> _LearnT:

        async def _raw(cap: str, sys_prompt: str, usr_message: str) -> str:
            return await self._raw_completion(cap, sys_prompt, usr_message, temperature=temperature)

        return await self._structured_completion_with_retry_async(
            capability,
            system_prompt,
            user_message,
            payload_model,
            raw_completion=_raw,
        )

    async def _raw_completion(
        self,
        capability: str,
        system_prompt: str,
        user_message: str,
        *,
        temperature: float,
    ) -> str:
        input_text = f"{system_prompt.strip()}\n\n{user_message.strip()}"

        async def _call() -> str:
            try:
                msg = await self._client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
            except AnthropicError as exc:
                raise self._transport_error(capability, exc) from exc

            parts: list[str] = []
            for block in msg.content:
                if block.type == "text":
                    parts.append(block.text)
            content = "".join(parts).strip()
            if not content:
                raise self._empty_content_error(capability)
            prompt_tokens, completion_tokens, total_tokens = extract_anthropic_token_usage(
                getattr(msg, "usage", None)
            )
            self._record_usage(
                capability,
                input_text=input_text,
                output_text=content,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                total_tokens=total_tokens,
            )
            return content

        return await self._run_logged_async(capability, _call)

    async def _stream_completion(
        self,
        capability: str,
        system_prompt: str,
        user_message: str,
        *,
        temperature: float,
    ) -> AsyncIterator[str]:
        input_text = f"{system_prompt.strip()}\n\n{user_message.strip()}"

        async def _factory() -> AsyncIterator[str]:
            emitted = False
            output_parts: list[str] = []
            try:
                stream_cm = self._client.messages.stream(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                async with stream_cm as active_stream:
                    async for text in active_stream.text_stream:
                        if text:
                            emitted = True
                            output_parts.append(text)
                            yield text
            except AnthropicError as exc:
                raise self._transport_error(capability, exc) from exc
            if not emitted:
                raise self._empty_content_error(capability)
            self._record_usage(
                capability,
                input_text=input_text,
                output_text="".join(output_parts),
            )

        async for fragment in self._stream_with_prompt_cache_async(
            capability,
            system_prompt,
            user_message,
            _factory,
        ):
            yield fragment

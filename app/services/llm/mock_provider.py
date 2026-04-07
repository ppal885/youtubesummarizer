import json
from collections.abc import AsyncIterator

from app.models.chapter_models import ChapterSegment
from app.models.qa_models import TranscriptChunkPassage
from app.models.response_models import DeveloperStudyDigest, QAResponse
from app.models.retrieval_models import RetrievalHit
from app.models.summary_models import ChunkSummary
from app.services.context_compression import heuristic_compressed_payload
from app.services.llm.base import LLMService
from app.services.llm.provider_support import LoggedLLMProviderMixin
from app.services.llm.schemas import (
    ChapterLlmItem,
    CompressedQaContextPayload,
    FlashcardItemPayload,
    FlashcardsPayload,
    GlossaryTermPayload,
    InterviewPrepEdgeCasePayload,
    InterviewPrepPayload,
    InterviewPrepQaPairPayload,
    InterviewPrepSystemDesignInsightPayload,
    LearningNotesPayload,
    MultiVideoSynthesisPayload,
    QaQueryUnderstandingPayload,
    QuizPayload,
    QuizQuestionPayload,
    VideoPairComparePayload,
)
from app.services.llm.suggested_questions_normalize import normalize_suggested_questions
from app.services.query_understanding import heuristic_query_understanding


class MockLLMService(LoggedLLMProviderMixin, LLMService):
    """Deterministic offline summarizer for local development and tests."""

    _provider_name = "mock"
    _model = "mock"
    _MAX_MERGED_BULLETS: int = 40
    _PREVIEW_CHARS: int = 240

    def _record_mock_usage(self, capability: str, *, input_text: str, output_text: str) -> None:
        self._record_usage(
            capability,
            input_text=input_text,
            output_text=output_text,
        )

    async def summarize_chunk(
        self,
        chunk: str,
        summary_type: str,
        *,
        learning_level: str = "intermediate",
    ) -> ChunkSummary:
        async def _call() -> ChunkSummary:
            stripped = chunk.strip()
            preview = stripped[: self._PREVIEW_CHARS].replace("\n", " ")
            if len(stripped) > self._PREVIEW_CHARS:
                preview = f"{preview}..."
            result = ChunkSummary(
                summary=(
                    f"[{summary_type}|{learning_level}] Mock chunk summary ({len(stripped)} characters). "
                    f"Excerpt: {preview}"
                ),
                bullets=[
                    f"Chunk theme ({summary_type}, {learning_level}): {len(stripped)} chars processed",
                    "Mock bullet: salient phrase extraction would run here with a real LLM.",
                ],
            )
            self._record_mock_usage(
                "summarize_chunk",
                input_text=f"summary_type={summary_type}\nlearning_level={learning_level}\n{chunk}",
                output_text=result.model_dump_json(),
            )
            return result

        return await self._run_logged_async("summarize_chunk", _call)

    async def merge_summaries(
        self,
        chunk_summaries: list[ChunkSummary],
        summary_type: str,
        *,
        learning_level: str = "intermediate",
    ) -> ChunkSummary:
        async def _call() -> ChunkSummary:
            if not chunk_summaries:
                return ChunkSummary(summary="", bullets=[])
            merged_bullets: list[str] = []
            for item in chunk_summaries:
                merged_bullets.extend(item.bullets)
            result = ChunkSummary(
                summary=(
                    f"[{summary_type}|{learning_level}] Final mock summary merged from "
                    f"{len(chunk_summaries)} chunk(s).\n\n"
                    + "\n\n".join(item.summary for item in chunk_summaries)
                ),
                bullets=merged_bullets[: self._MAX_MERGED_BULLETS],
            )
            self._record_mock_usage(
                "merge_summaries",
                input_text=json.dumps(
                    [item.model_dump(mode="json") for item in chunk_summaries],
                    ensure_ascii=False,
                ),
                output_text=result.model_dump_json(),
            )
            return result

        return await self._run_logged_async("merge_summaries", _call)

    async def answer_question(
        self,
        question: str,
        context_passages: list[TranscriptChunkPassage],
        *,
        orientation_notes: str | None = None,
        evidence_synthesis_notes: str | None = None,
    ) -> QAResponse:
        _ = orientation_notes
        _ = evidence_synthesis_notes

        async def _call() -> QAResponse:
            if not context_passages:
                return QAResponse(
                    answer="Not found in context: no transcript passages were retrieved for this question."
                )
            preview = question.strip()[:120]
            if len(question.strip()) > 120:
                preview += "..."
            parts = [
                f"[mock QA] Answering from {len(context_passages)} chunk(s).",
                f"Question (preview): {preview}",
            ]
            for passage in context_passages[:3]:
                excerpt = passage.text.strip()[:160].replace("\n", " ")
                if len(passage.text) > 160:
                    excerpt += "..."
                parts.append(f"@ {passage.time_display} (#{passage.chunk_index}): {excerpt}")
            result = QAResponse(answer=" ".join(parts))
            self._record_mock_usage(
                "answer_question",
                input_text=question + "\n" + "\n".join(p.text for p in context_passages),
                output_text=result.model_dump_json(),
            )
            return result

        return await self._run_logged_async("answer_question", _call)

    async def answer_question_stream(
        self,
        question: str,
        context_passages: list[TranscriptChunkPassage],
        *,
        orientation_notes: str | None = None,
        evidence_synthesis_notes: str | None = None,
    ) -> AsyncIterator[str]:
        resp = await self.answer_question(
            question,
            context_passages,
            orientation_notes=orientation_notes,
            evidence_synthesis_notes=evidence_synthesis_notes,
        )
        text = resp.answer

        async def _factory() -> AsyncIterator[str]:
            if len(text) <= 100:
                yield text
                return
            third = len(text) // 3
            yield text[:third]
            yield text[third : 2 * third]
            yield text[2 * third :]

        async for chunk in self._iter_logged_async("answer_question_stream", _factory):
            yield chunk

    async def compress_qa_retrieval_context(
        self,
        question: str,
        hits: list[RetrievalHit],
        target_count: int,
    ) -> CompressedQaContextPayload:
        async def _call() -> CompressedQaContextPayload:
            payload = heuristic_compressed_payload(hits, target_count)
            self._record_mock_usage(
                "compress_qa_retrieval_context",
                input_text=question + "\n" + "\n".join(hit.passage.text for hit in hits),
                output_text=payload.model_dump_json(),
            )
            return payload

        return await self._run_logged_async("compress_qa_retrieval_context", _call)

    async def generate_suggested_questions(self, transcript: str) -> list[str]:
        async def _call() -> list[str]:
            preview = transcript.strip().replace("\n", " ")
            snippet = preview[:50] + ("..." if len(preview) > 50 else "")
            result = normalize_suggested_questions(
                [
                    "What is this video mainly about?",
                    "What key terms or concepts does the speaker introduce?",
                    (
                        f"What is highlighted near the start: {snippet}?"
                        if snippet
                        else "What does the speaker establish at the beginning?"
                    ),
                    "What steps, causes, or examples does the video describe?",
                    "Why might this topic matter to the audience?",
                    "What deeper detail or nuance does the speaker add later?",
                    "How would you summarize the takeaway in one sentence?",
                    "What might someone new to this topic ask next?",
                ]
            )
            self._record_mock_usage(
                "generate_suggested_questions",
                input_text=transcript,
                output_text=json.dumps(result, ensure_ascii=False),
            )
            return result

        return await self._run_logged_async("generate_suggested_questions", _call)

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
        _ = bullets_1
        _ = bullets_2

        async def _cmp() -> VideoPairComparePayload:
            return self._mock_compare_payload(
                title_1=title_1,
                summary_1=summary_1,
                title_2=title_2,
                summary_2=summary_2,
            )

        return await self._run_logged_async("compare_two_video_summaries", _cmp)

    async def synthesize_multi_video_summaries(self, user_message: str) -> MultiVideoSynthesisPayload:
        async def _call() -> MultiVideoSynthesisPayload:
            topic_line = next(
                (line for line in user_message.splitlines() if line.startswith("TOPIC:")),
                "TOPIC: (unknown)",
            )
            result = MultiVideoSynthesisPayload(
                combined_summary=(
                    f"[mock] Combined view across videos ({len(user_message.strip())} chars in prompt). "
                    f"{topic_line} Real synthesis uses transcript-derived summaries only."
                ),
                common_ideas=[
                    "[mock] All inputs are YouTube transcript summaries under the same topic lens.",
                    "[mock] Each block includes title, summary, and bullets from the pipeline.",
                ],
                differences=[
                    "[mock] Titles and bullet lists differ per video as in the user message.",
                ],
                best_explanation=(
                    "[mock] Prefer the video whose summary block is most specific to the topic; "
                    "with a real LLM, this sentence names titles from the prompt."
                ),
            )
            self._record_mock_usage(
                "synthesize_multi_video_summaries",
                input_text=user_message,
                output_text=result.model_dump_json(),
            )
            return result

        return await self._run_logged_async("synthesize_multi_video_summaries", _call)

    async def generate_study_notes(self, user_message: str) -> LearningNotesPayload:
        async def _call() -> LearningNotesPayload:
            preview = user_message.strip()[:100].replace("\n", " ")
            if len(user_message.strip()) > 100:
                preview += "..."
            result = LearningNotesPayload(
                concise_notes=f"[mock] Quick review ({len(user_message.strip())} chars in prompt). {preview}",
                detailed_notes=(
                    "[mock] Expanded notes would mirror the time-labeled transcript only.\n"
                    f"- Prompt length: {len(user_message.strip())} characters.\n"
                    "- No facts beyond the supplied caption text."
                ),
                glossary_terms=[
                    GlossaryTermPayload(term="[mock] transcript", definition="Caption text supplied in the user message."),
                    GlossaryTermPayload(term="[mock] video", definition="Source video the captions were taken from."),
                ],
            )
            self._record_mock_usage(
                "generate_study_notes",
                input_text=user_message,
                output_text=result.model_dump_json(),
            )
            return result

        return await self._run_logged_async("generate_study_notes", _call)

    async def generate_quiz(self, user_message: str) -> QuizPayload:
        async def _call() -> QuizPayload:
            count = len(user_message.strip())
            result = QuizPayload(
                questions=[
                    QuizQuestionPayload(
                        question="[mock] What is the source text for this quiz?",
                        options=[
                            "The video transcript only",
                            "A random textbook",
                            "Social media comments",
                            "No source",
                        ],
                        correct_index=0,
                        explanation="Mock quiz items are designed to be grounded in the fetched transcript.",
                    ),
                    QuizQuestionPayload(
                        question="[mock] Roughly how long is the transcript (characters)?",
                        options=[str(max(1, count)), "0", "999999", "Unknown without counting"],
                        correct_index=0,
                        explanation="The mock uses the actual transcript length for one distractor-free check.",
                    ),
                ]
            )
            self._record_mock_usage(
                "generate_quiz",
                input_text=user_message,
                output_text=result.model_dump_json(),
            )
            return result

        return await self._run_logged_async("generate_quiz", _call)

    async def generate_chapters(self, segments: list[ChapterSegment]) -> list[ChapterLlmItem]:
        async def _call() -> list[ChapterLlmItem]:
            out: list[ChapterLlmItem] = []
            for index, segment in enumerate(segments):
                preview = segment.text[:120].replace("\n", " ")
                if len(segment.text) > 120:
                    preview += "..."
                out.append(
                    ChapterLlmItem(
                        title=f"Chapter {index + 1} (~{segment.start_seconds:.0f}s)",
                        short_summary=preview or "-",
                    )
                )
            self._record_mock_usage(
                "generate_chapters",
                input_text="\n".join(segment.text for segment in segments),
                output_text=json.dumps([item.model_dump(mode="json") for item in out], ensure_ascii=False),
            )
            return out

        return await self._run_logged_async("generate_chapters", _call)

    async def generate_flashcards(self, user_message: str) -> FlashcardsPayload:
        async def _call() -> FlashcardsPayload:
            stripped = user_message.strip()
            head = stripped[:60].replace("\n", " ")
            tail = "..." if len(stripped) > 60 else ""
            timestamp = 0.0 if "start_seconds=0.00" in user_message or "start_seconds=0.0" in user_message else None
            result = FlashcardsPayload(
                cards=[
                    FlashcardItemPayload(
                        front="[mock] What are you studying from?",
                        back="Caption text merged from the YouTube transcript (no side knowledge).",
                        timestamp_seconds=timestamp,
                    ),
                    FlashcardItemPayload(
                        front="[mock] Transcript length?",
                        back=f"About {len(stripped)} characters in the provided prompt.",
                        timestamp_seconds=None,
                    ),
                    FlashcardItemPayload(
                        front="[mock] First words in prompt?",
                        back=f"{head}{tail}" if head else "Transcript was very short.",
                        timestamp_seconds=None,
                    ),
                ]
            )
            self._record_mock_usage(
                "generate_flashcards",
                input_text=user_message,
                output_text=result.model_dump_json(),
            )
            return result

        return await self._run_logged_async("generate_flashcards", _call)

    async def understand_qa_query(self, question: str) -> QaQueryUnderstandingPayload:
        async def _call() -> QaQueryUnderstandingPayload:
            payload = heuristic_query_understanding(question)
            self._record_mock_usage(
                "understand_qa_query",
                input_text=question,
                output_text=payload.model_dump_json(),
            )
            return payload

        return await self._run_logged_async("understand_qa_query", _call)

    async def generate_developer_study_digest(self, user_message: str) -> DeveloperStudyDigest:
        async def _call() -> DeveloperStudyDigest:
            count = len(user_message.strip())
            result = DeveloperStudyDigest(
                concepts=[
                    f"[mock] Labeled transcript length ~{count} characters (developer digest is transcript-grounded in production).",
                ],
                tools=["[mock] Listed only when the speaker names a tool in the captions."],
                patterns=["[mock] Named or described patterns from the transcript only."],
                best_practices=["[mock] Advice the speaker explicitly recommends in the transcript."],
                pitfalls=["[mock] Mistakes or warnings the speaker calls out in the transcript."],
                pseudo_code=(
                    "procedure mock_flow():\n"
                    "  // Real mode fills this when the video walks through code or APIs.\n"
                    "  return structured_placeholder\n"
                ),
                explanation=(
                    "1. The mock receives the same labeled-caption prompt as production.\n"
                    "2. A real LLM would extract steps and APIs mentioned in those lines only."
                ),
            )
            self._record_mock_usage(
                "generate_developer_study_digest",
                input_text=user_message,
                output_text=result.model_dump_json(),
            )
            return result

        return await self._run_logged_async("generate_developer_study_digest", _call)

    async def generate_interview_prep(self, user_message: str) -> InterviewPrepPayload:
        async def _call() -> InterviewPrepPayload:
            stripped = user_message.strip()
            preview = stripped[:80].replace("\n", " ")
            if len(stripped) > 80:
                preview += "..."
            result = InterviewPrepPayload(
                key_questions=[
                    InterviewPrepQaPairPayload(
                        question="[mock] Summarize what this video transcript is primarily about.",
                        answer=(
                            f"The prompt contains a time-labeled transcript (~{len(stripped)} characters). "
                            f"Opening: {preview or '-'}"
                        ),
                    ),
                    InterviewPrepQaPairPayload(
                        question="[mock] How would you verify claims when turning this into interview prep?",
                        answer="Cross-check every bullet against the labeled chunks only; omit anything not spoken.",
                    ),
                    InterviewPrepQaPairPayload(
                        question="[mock] What is one limitation of mock interview prep?",
                        answer="Deterministic placeholders replace a real model; use a configured LLM for production.",
                    ),
                ],
                system_design_insights=[
                    InterviewPrepSystemDesignInsightPayload(
                        title="Transcript as source of truth",
                        insight=(
                            "Interview answers should trace back to specific ideas in the caption text, "
                            "not generic blog patterns."
                        ),
                    ),
                ],
                edge_cases=[
                    InterviewPrepEdgeCasePayload(
                        scenario="Transcript is very short or mostly music/noise.",
                        discussion="Return fewer Q&A pairs and avoid inventing system-design content.",
                    ),
                    InterviewPrepEdgeCasePayload(
                        scenario="Speaker uses vague hand-waving without concrete detail.",
                        discussion="Flag uncertainty in answers rather than fabricating precise metrics.",
                    ),
                ],
            )
            self._record_mock_usage(
                "generate_interview_prep",
                input_text=user_message,
                output_text=result.model_dump_json(),
            )
            return result

        return await self._run_logged_async("generate_interview_prep", _call)

    def _mock_compare_payload(
        self,
        *,
        title_1: str,
        summary_1: str,
        title_2: str,
        summary_2: str,
    ) -> VideoPairComparePayload:
        result = VideoPairComparePayload(
            similarities=[
                "[mock compare] Both summaries were produced from transcript text only (no live video).",
            ],
            differences=[
                (
                    f"[mock] Video 1 emphasizes: {summary_1[:100]}..."
                    if len(summary_1) > 100
                    else f"[mock] Video 1: {summary_1}"
                ),
                (
                    f"[mock] Video 2 emphasizes: {summary_2[:100]}..."
                    if len(summary_2) > 100
                    else f"[mock] Video 2: {summary_2}"
                ),
                f"[mock] Titles differ: '{title_1[:48]}' vs '{title_2[:48]}'.",
            ],
        )
        self._record_mock_usage(
            "compare_two_video_summaries",
            input_text=f"{title_1}\n{summary_1}\n{title_2}\n{summary_2}",
            output_text=result.model_dump_json(),
        )
        return result

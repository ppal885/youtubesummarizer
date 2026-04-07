import uuid

from app.config import Settings
from app.exceptions import InvalidYouTubeUrlError, LLMInvocationError, TranscriptFetchError
from app.models.request_models import TranscriptLearningRequest
from app.models.response_models import (
    FlashcardItem,
    FlashcardsResponse,
    GlossaryTerm,
    InterviewPrepEdgeCase,
    InterviewPrepQaItem,
    InterviewPrepResponse,
    InterviewPrepSystemDesignInsight,
    NotesResponse,
    QuizQuestionItem,
    QuizResponse,
)
from app.services.learning_transcript import load_learning_transcript_context
from app.services.llm import LLMService, get_llm_service
from app.services.llm.learning_prompting import build_labeled_transcript_user_message
from app.services.llm.schemas import InterviewPrepPayload, QuizQuestionPayload
from app.observability.llm_request_usage import llm_request_usage_context
from app.observability.request_context import trace_context
from app.utils.output_normalizer import (
    normalize_flashcards_response,
    normalize_interview_prep_response,
    normalize_notes_response,
    normalize_quiz_response,
)
from app.utils.time_utils import format_seconds_hh_mm_ss


def _normalize_quiz_questions(raw: list[QuizQuestionPayload]) -> list[QuizQuestionItem]:
    out: list[QuizQuestionItem] = []
    for q in raw:
        opts = [o.strip() for o in q.options if o and str(o).strip()]
        if len(opts) != 4:
            continue
        idx = int(q.correct_index)
        if idx < 0 or idx > 3:
            continue
        qtext = q.question.strip()
        if not qtext:
            continue
        expl = (q.explanation or "").strip()
        answer_text = opts[idx]
        out.append(
            QuizQuestionItem(
                question=qtext,
                options=opts,
                answer=answer_text,
                explanation=expl or "See transcript for supporting detail.",
            )
        )
    return out


def _snap_flashcard_timestamp(
    raw: float | None,
    allowed: frozenset[float],
) -> tuple[float | None, str | None]:
    if raw is None or not allowed:
        return None, None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None, None
    best = min(allowed, key=lambda x: abs(x - v))
    if abs(best - v) <= 5.0:
        return best, format_seconds_hh_mm_ss(best)
    return None, None


class LearningService:
    """Transcript-grounded study artifacts using the same chunking path as summarization."""

    def __init__(self, settings: Settings, llm: LLMService) -> None:
        self._settings = settings
        self._llm = llm

    def _context(self, request: TranscriptLearningRequest):
        return load_learning_transcript_context(request, self._settings)

    async def notes(self, request: TranscriptLearningRequest) -> NotesResponse:
        ctx = self._context(request)
        with trace_context(str(uuid.uuid4())), llm_request_usage_context(
            endpoint="notes",
            video_id=ctx.video_id,
        ):
            user_message = build_labeled_transcript_user_message(ctx.labeled_transcript)
            payload = await self._llm.generate_study_notes(user_message)
            glossary = [
                GlossaryTerm(term=g.term.strip(), definition=(g.definition or "").strip())
                for g in payload.glossary_terms
                if g.term.strip()
            ]
            return normalize_notes_response(NotesResponse(
                video_id=ctx.video_id,
                title=ctx.title,
                concise_notes=payload.concise_notes.strip(),
                detailed_notes=payload.detailed_notes.strip(),
                glossary_terms=glossary,
            ))

    async def quiz(self, request: TranscriptLearningRequest) -> QuizResponse:
        ctx = self._context(request)
        with trace_context(str(uuid.uuid4())), llm_request_usage_context(
            endpoint="quiz",
            video_id=ctx.video_id,
        ):
            user_message = build_labeled_transcript_user_message(ctx.labeled_transcript)
            payload = await self._llm.generate_quiz(user_message)
            questions = _normalize_quiz_questions(payload.questions)
            if not questions:
                raise LLMInvocationError("Quiz generation returned no valid multiple-choice items.")
            return normalize_quiz_response(
                QuizResponse(video_id=ctx.video_id, title=ctx.title, questions=questions)
            )

    async def flashcards(self, request: TranscriptLearningRequest) -> FlashcardsResponse:
        ctx = self._context(request)
        with trace_context(str(uuid.uuid4())), llm_request_usage_context(
            endpoint="flashcards",
            video_id=ctx.video_id,
        ):
            user_message = build_labeled_transcript_user_message(ctx.labeled_transcript)
            payload = await self._llm.generate_flashcards(user_message)
            allowed = frozenset(c.start_seconds for c in ctx.chunks)
            cards: list[FlashcardItem] = []
            for c in payload.cards:
                front = c.front.strip()
                back = c.back.strip()
                if not front or not back:
                    continue
                ts, ft = _snap_flashcard_timestamp(c.timestamp_seconds, allowed)
                cards.append(
                    FlashcardItem(
                        front=front,
                        back=back,
                        timestamp_seconds=ts,
                        formatted_time=ft,
                    )
                )
            if not cards:
                raise LLMInvocationError("Flashcard generation returned no valid cards.")
            return normalize_flashcards_response(
                FlashcardsResponse(video_id=ctx.video_id, title=ctx.title, cards=cards)
            )

    async def interview_prep(self, request: TranscriptLearningRequest) -> InterviewPrepResponse:
        ctx = self._context(request)
        with trace_context(str(uuid.uuid4())), llm_request_usage_context(
            endpoint="interview-prep",
            video_id=ctx.video_id,
        ):
            user_message = build_labeled_transcript_user_message(ctx.labeled_transcript)
            payload = await self._llm.generate_interview_prep(user_message)
            key_questions, system_rows, edge_rows = _normalize_interview_prep(payload)
            if not key_questions:
                raise LLMInvocationError("Interview prep returned no valid question-and-answer pairs.")
            return normalize_interview_prep_response(InterviewPrepResponse(
                video_id=ctx.video_id,
                title=ctx.title,
                key_questions=key_questions,
                system_design_insights=system_rows,
                edge_cases=edge_rows,
            ))


def _normalize_interview_prep(
    payload: InterviewPrepPayload,
) -> tuple[list[InterviewPrepQaItem], list[InterviewPrepSystemDesignInsight], list[InterviewPrepEdgeCase]]:
    key_questions: list[InterviewPrepQaItem] = []
    for item in payload.key_questions:
        q = item.question.strip()
        a = item.answer.strip()
        if q and a:
            key_questions.append(InterviewPrepQaItem(question=q, answer=a))

    system_design_insights: list[InterviewPrepSystemDesignInsight] = []
    for row in payload.system_design_insights:
        title = row.title.strip()
        insight = row.insight.strip()
        if title and insight:
            system_design_insights.append(InterviewPrepSystemDesignInsight(title=title, insight=insight))

    edge_cases: list[InterviewPrepEdgeCase] = []
    for row in payload.edge_cases:
        scenario = row.scenario.strip()
        discussion = row.discussion.strip()
        if scenario and discussion:
            edge_cases.append(InterviewPrepEdgeCase(scenario=scenario, discussion=discussion))

    return key_questions, system_design_insights, edge_cases


def build_default_learning_service(settings: Settings) -> LearningService:
    return LearningService(settings=settings, llm=get_llm_service(settings))

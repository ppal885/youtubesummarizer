from __future__ import annotations

from collections.abc import Iterable

from app.models.response_models import (
    AskCitationSource,
    AskResponse,
    CompareVideosResponse,
    DeveloperStudyDigest,
    FinalSummary,
    FlashcardItem,
    FlashcardsResponse,
    GlossaryTerm,
    InterviewPrepEdgeCase,
    InterviewPrepQaItem,
    InterviewPrepResponse,
    InterviewPrepSystemDesignInsight,
    KeyMoment,
    NotesResponse,
    QuizQuestionItem,
    QuizResponse,
    SynthesizeResponse,
    VideoChapter,
)
from app.utils.text_consistency import (
    canonical_dedupe_key,
    clean_text,
    dedupe_text_items,
    normalize_bullet_list,
    normalize_bullet_text,
    normalize_text_block,
    normalize_timestamp,
    normalize_timestamp_text,
)

# Backward-compatible alias for internal callers / tests that imported patterns.
_canonical_text_key = canonical_dedupe_key


def normalize_ask_source(source: AskCitationSource) -> AskCitationSource:
    formatted_time = normalize_timestamp(source.start_time) or normalize_timestamp_text(source.formatted_time) or "00:00"
    return AskCitationSource(
        start_time=source.start_time,
        formatted_time=formatted_time,
        text=clean_text(source.text),
    )


def normalize_ask_response(response: AskResponse) -> AskResponse:
    sources = _dedupe_ask_sources(response.sources)
    return AskResponse(
        answer=clean_text(response.answer),
        sources=sources,
        confidence=float(response.confidence),
        confidence_score=float(response.confidence_score),
    )


def normalize_final_summary(result: FinalSummary) -> FinalSummary:
    return FinalSummary(
        video_id=result.video_id,
        title=clean_text(result.title),
        summary=clean_text(result.summary),
        bullets=normalize_bullet_list(result.bullets),
        key_moments=_normalize_key_moments(result.key_moments),
        transcript_length=result.transcript_length,
        chunks_processed=result.chunks_processed,
        learning_level=result.learning_level,
        suggested_questions=dedupe_text_items(result.suggested_questions),
        chapters=_normalize_video_chapters(result.chapters),
        developer_digest=_normalize_developer_digest(result.developer_digest),
    )


def normalize_notes_response(response: NotesResponse) -> NotesResponse:
    return NotesResponse(
        video_id=response.video_id,
        title=clean_text(response.title),
        concise_notes=normalize_text_block(response.concise_notes),
        detailed_notes=normalize_text_block(response.detailed_notes),
        glossary_terms=_normalize_glossary_terms(response.glossary_terms),
    )


def normalize_quiz_response(response: QuizResponse) -> QuizResponse:
    questions: list[QuizQuestionItem] = []
    seen: set[str] = set()
    for item in response.questions:
        question = clean_text(item.question)
        key = _canonical_text_key(question)
        if not key or key in seen:
            continue
        seen.add(key)
        options = [clean_text(option) for option in item.options if clean_text(option)]
        answer = clean_text(item.answer)
        questions.append(
            QuizQuestionItem(
                question=question,
                options=options,
                answer=answer,
                explanation=clean_text(item.explanation),
            )
        )
    return QuizResponse(
        video_id=response.video_id,
        title=clean_text(response.title),
        questions=questions,
    )


def normalize_flashcards_response(response: FlashcardsResponse) -> FlashcardsResponse:
    cards: list[FlashcardItem] = []
    seen: set[tuple[str, str]] = set()
    for item in response.cards:
        front = clean_text(item.front)
        back = normalize_text_block(item.back)
        key = (_canonical_text_key(front), _canonical_text_key(back))
        if not key[0] or not key[1] or key in seen:
            continue
        seen.add(key)
        formatted_time = normalize_timestamp(item.timestamp_seconds) or normalize_timestamp_text(item.formatted_time)
        cards.append(
            FlashcardItem(
                front=front,
                back=back,
                timestamp_seconds=item.timestamp_seconds,
                formatted_time=formatted_time,
            )
        )
    return FlashcardsResponse(
        video_id=response.video_id,
        title=clean_text(response.title),
        cards=cards,
    )


def normalize_interview_prep_response(response: InterviewPrepResponse) -> InterviewPrepResponse:
    return InterviewPrepResponse(
        video_id=response.video_id,
        title=clean_text(response.title),
        key_questions=_normalize_interview_questions(response.key_questions),
        system_design_insights=_normalize_system_design_insights(response.system_design_insights),
        edge_cases=_normalize_edge_cases(response.edge_cases),
    )


def normalize_developer_digest(digest: DeveloperStudyDigest | None) -> DeveloperStudyDigest | None:
    return _normalize_developer_digest(digest)


def normalize_compare_response(response: CompareVideosResponse) -> CompareVideosResponse:
    return CompareVideosResponse(
        summary_1=clean_text(response.summary_1),
        summary_2=clean_text(response.summary_2),
        similarities=normalize_bullet_list(response.similarities),
        differences=normalize_bullet_list(response.differences),
    )


def normalize_synthesize_response(response: SynthesizeResponse) -> SynthesizeResponse:
    return SynthesizeResponse(
        combined_summary=clean_text(response.combined_summary),
        common_ideas=normalize_bullet_list(response.common_ideas),
        differences=normalize_bullet_list(response.differences),
        best_explanation=clean_text(response.best_explanation),
    )


def _normalize_key_moments(items: Iterable[KeyMoment]) -> list[KeyMoment]:
    output: list[KeyMoment] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        timestamp = normalize_timestamp_text(item.time) or "00:00"
        note = clean_text(item.note) or "-"
        key = (timestamp, _canonical_text_key(note))
        if key in seen:
            continue
        seen.add(key)
        output.append(KeyMoment(time=timestamp, note=note))
    return output


def _normalize_video_chapters(items: Iterable[VideoChapter]) -> list[VideoChapter]:
    output: list[VideoChapter] = []
    for item in items:
        formatted_time = normalize_timestamp(item.start_time) or normalize_timestamp_text(item.formatted_time) or "00:00"
        output.append(
            VideoChapter(
                title=clean_text(item.title) or "Untitled segment",
                start_time=item.start_time,
                formatted_time=formatted_time,
                short_summary=clean_text(item.short_summary) or "-",
            )
        )
    return output


def _normalize_glossary_terms(items: Iterable[GlossaryTerm]) -> list[GlossaryTerm]:
    output: list[GlossaryTerm] = []
    seen: set[str] = set()
    for item in items:
        term = clean_text(item.term)
        key = _canonical_text_key(term)
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(
            GlossaryTerm(
                term=term,
                definition=clean_text(item.definition),
            )
        )
    return output


def _normalize_developer_digest(digest: DeveloperStudyDigest | None) -> DeveloperStudyDigest | None:
    if digest is None:
        return None
    return DeveloperStudyDigest(
        concepts=dedupe_text_items(digest.concepts, normalizer=normalize_bullet_text),
        tools=dedupe_text_items(digest.tools, normalizer=normalize_bullet_text),
        patterns=dedupe_text_items(digest.patterns, normalizer=normalize_bullet_text),
        best_practices=dedupe_text_items(digest.best_practices, normalizer=normalize_bullet_text),
        pitfalls=dedupe_text_items(digest.pitfalls, normalizer=normalize_bullet_text),
        pseudo_code=digest.pseudo_code.strip(),
        explanation=normalize_text_block(digest.explanation),
    )


def _normalize_interview_questions(items: Iterable[InterviewPrepQaItem]) -> list[InterviewPrepQaItem]:
    output: list[InterviewPrepQaItem] = []
    seen: set[str] = set()
    for item in items:
        question = clean_text(item.question)
        key = _canonical_text_key(question)
        if not key or key in seen:
            continue
        seen.add(key)
        answer = normalize_text_block(item.answer)
        output.append(InterviewPrepQaItem(question=question, answer=answer))
    return output


def _normalize_system_design_insights(
    items: Iterable[InterviewPrepSystemDesignInsight],
) -> list[InterviewPrepSystemDesignInsight]:
    output: list[InterviewPrepSystemDesignInsight] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        title = clean_text(item.title)
        insight = normalize_text_block(item.insight)
        key = (_canonical_text_key(title), _canonical_text_key(insight))
        if not key[0] or not key[1] or key in seen:
            continue
        seen.add(key)
        output.append(InterviewPrepSystemDesignInsight(title=title, insight=insight))
    return output


def _normalize_edge_cases(items: Iterable[InterviewPrepEdgeCase]) -> list[InterviewPrepEdgeCase]:
    output: list[InterviewPrepEdgeCase] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        scenario = clean_text(item.scenario)
        discussion = normalize_text_block(item.discussion)
        key = (_canonical_text_key(scenario), _canonical_text_key(discussion))
        if not key[0] or not key[1] or key in seen:
            continue
        seen.add(key)
        output.append(InterviewPrepEdgeCase(scenario=scenario, discussion=discussion))
    return output


def _dedupe_ask_sources(items: Iterable[AskCitationSource]) -> list[AskCitationSource]:
    output: list[AskCitationSource] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        normalized = normalize_ask_source(item)
        key = (
            normalized.formatted_time,
            _canonical_text_key(normalized.text),
        )
        if not key[1] or key in seen:
            continue
        seen.add(key)
        output.append(normalized)
    return output

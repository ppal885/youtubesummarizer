import asyncio
import time
from typing import Any

from app.config import Settings
from app.demo.catalog import (
    DEMO_VIDEO_ID,
    demo_developer_digest,
    demo_final_summary,
    is_demo_video_for_settings,
)
from app.exceptions import InvalidYouTubeUrlError, LLMInvocationError, TranscriptFetchError
from app.models.request_models import SummarizeRequest, SummaryType
from app.models.response_models import (
    DeveloperStudyDigest,
    FinalSummary,
    KeyMoment,
    PipelinePerformanceMs,
    VideoChapter,
)
from app.observability.llm_request_usage import llm_request_usage_context
from app.models.transcript_models import TranscriptTextChunk
from app.observability.request_context import trace_context
from app.observability.summarize_pipeline import log_summarize_line
from app.services.chapter_pipeline import build_video_chapters
from app.services.chunk_service import chunk_transcript_items
from app.services.learning_transcript import format_labeled_chunks
from app.services.llm import LLMService, get_llm_service
from app.services.llm.learning_prompting import build_labeled_transcript_user_message
from app.services.summary_cache import CachedSummaryPayload, SummaryMemoryCache, get_summary_memory_cache
from app.services.transcript_service import fetch_transcript_items, merge_transcript_text
from app.services.youtube_service import extract_video_id, fetch_video_title
from app.utils.time_utils import format_seconds_hh_mm_ss
from app.utils.output_normalizer import normalize_final_summary

_MAX_TRANSCRIPT_CHARS_FOR_SUGGESTIONS = 14_000
_MAX_LABELED_TRANSCRIPT_CHARS_FOR_DEVELOPER = 18_000


def _ms(start: float, end: float) -> float:
    return round((end - start) * 1000, 2)


class SummaryService:
    def __init__(
        self,
        settings: Settings,
        llm: LLMService,
        *,
        summary_cache: SummaryMemoryCache | None = None,
    ) -> None:
        self._settings = settings
        self._llm = llm
        self._cache = summary_cache if summary_cache is not None else get_summary_memory_cache()

    async def summarize_from_url(self, request: SummarizeRequest, *, trace_id: str) -> FinalSummary:
        video_id_hint = extract_video_id(str(request.url))
        with trace_context(trace_id), llm_request_usage_context(
            endpoint="summarize",
            video_id=video_id_hint,
        ):
            url = str(request.url)
            summary_type: SummaryType = request.summary_type
            language = request.language
            developer_mode = request.developer_mode
            t0 = time.perf_counter()
            llm_provider = self._settings.llm_provider
            llm_model = self._settings.llm_model

            log_summarize_line(
                "summarize.pipeline.start",
                trace_id=trace_id,
                summary_type=summary_type,
                language=language,
                llm_provider=llm_provider,
                llm_model=llm_model,
            )

            video_id = video_id_hint
            if video_id is None:
                raise InvalidYouTubeUrlError(
                    "Could not parse a valid YouTube video id from the provided URL."
                )

            if is_demo_video_for_settings(self._settings, video_id):
                total_demo = _ms(t0, time.perf_counter())
                demo_perf = PipelinePerformanceMs(
                    transcript_fetch_ms=0.0,
                    chunking_ms=0.0,
                    llm_ms=0.0,
                    total_ms=total_demo,
                )
                log_summarize_line(
                    "summarize.pipeline.demo_preloaded",
                    trace_id=trace_id,
                    video_id=DEMO_VIDEO_ID,
                    summary_type=summary_type,
                    language=language,
                    llm_provider=llm_provider,
                    llm_model=llm_model,
                    elapsed_ms=total_demo,
                )
                log_summarize_line(
                    "summarize.pipeline.metrics",
                    trace_id=trace_id,
                    video_id=DEMO_VIDEO_ID,
                    transcript_fetch_ms=demo_perf.transcript_fetch_ms,
                    chunking_ms=demo_perf.chunking_ms,
                    llm_ms=demo_perf.llm_ms,
                    total_ms=demo_perf.total_ms,
                    demo_mode=True,
                )
                base = normalize_final_summary(
                    demo_final_summary().model_copy(
                        update={"learning_level": request.learning_level, "performance": demo_perf}
                    )
                )
                if developer_mode:
                    return normalize_final_summary(
                        base.model_copy(update={"developer_digest": demo_developer_digest()})
                    )
                return base

            learning_level = request.learning_level
            title = fetch_video_title(url)
            t_tf0 = time.perf_counter()
            items = fetch_transcript_items(video_id, language)
            merged_text = merge_transcript_text(items)
            if not merged_text.strip():
                raise TranscriptFetchError("Transcript was empty after cleaning.")

            transcript_length = len(merged_text)
            t_after_transcript = time.perf_counter()
            transcript_fetch_ms = _ms(t_tf0, t_after_transcript)
            log_summarize_line(
                "summarize.pipeline.transcript_fetched",
                trace_id=trace_id,
                video_id=video_id,
                transcript_length=transcript_length,
                elapsed_ms=_ms(t0, t_after_transcript),
            )

            t_ch0 = time.perf_counter()
            text_chunks: list[TranscriptTextChunk] = chunk_transcript_items(items, self._settings)
            chunk_count = len(text_chunks)
            t_after_chunk = time.perf_counter()
            chunking_ms = _ms(t_ch0, t_after_chunk)
            log_summarize_line(
                "summarize.pipeline.chunked",
                trace_id=trace_id,
                video_id=video_id,
                transcript_length=transcript_length,
                chunk_count=chunk_count,
                elapsed_ms=_ms(t0, t_after_chunk),
            )

            cached = self._cache.get(video_id, summary_type, learning_level, developer_mode)
            if cached is not None:
                log_summarize_line(
                    "summarize.pipeline.cache_hit",
                    trace_id=trace_id,
                    video_id=video_id,
                    summary_type=summary_type,
                    transcript_length=transcript_length,
                    chunk_count=chunk_count,
                    elapsed_ms=_ms(t0, time.perf_counter()),
                )
                key_moments = self._build_key_moments(text_chunks)
                chapters = await self._safe_chapters(text_chunks, cached_chapters=cached.chapters)
                dev_digest: DeveloperStudyDigest | None = None
                if cached.developer_digest is not None:
                    try:
                        dev_digest = DeveloperStudyDigest.model_validate(cached.developer_digest)
                    except (ValueError, TypeError):
                        dev_digest = None
                t_cache_done = time.perf_counter()
                cache_perf = PipelinePerformanceMs(
                    transcript_fetch_ms=transcript_fetch_ms,
                    chunking_ms=chunking_ms,
                    llm_ms=0.0,
                    total_ms=_ms(t0, t_cache_done),
                )
                log_summarize_line(
                    "summarize.pipeline.metrics",
                    trace_id=trace_id,
                    video_id=video_id,
                    transcript_fetch_ms=cache_perf.transcript_fetch_ms,
                    chunking_ms=cache_perf.chunking_ms,
                    llm_ms=cache_perf.llm_ms,
                    total_ms=cache_perf.total_ms,
                    cache_hit=True,
                )
                return normalize_final_summary(
                    FinalSummary(
                        video_id=video_id,
                        title=title,
                        summary=cached.summary,
                        bullets=list(cached.bullets),
                        key_moments=key_moments,
                        transcript_length=transcript_length,
                        chunks_processed=chunk_count,
                        learning_level=learning_level,
                        suggested_questions=list(cached.suggested_questions),
                        chapters=chapters,
                        developer_digest=dev_digest,
                        performance=cache_perf,
                    )
                )

            t_llm_start = time.perf_counter()
            chunk_summaries = await asyncio.gather(
                *[
                    self._llm.summarize_chunk(chunk.text, summary_type, learning_level=learning_level)
                    for chunk in text_chunks
                ]
            )
            final = await self._llm.merge_summaries(
                chunk_summaries,
                summary_type,
                learning_level=learning_level,
            )

            transcript_for_questions = merged_text
            if len(transcript_for_questions) > _MAX_TRANSCRIPT_CHARS_FOR_SUGGESTIONS:
                transcript_for_questions = transcript_for_questions[
                    :_MAX_TRANSCRIPT_CHARS_FOR_SUGGESTIONS
                ]
            suggested_questions = await self._llm.generate_suggested_questions(transcript_for_questions)
            t_after_core_llm = time.perf_counter()
            summarization_ms = _ms(t_llm_start, t_after_core_llm)
            log_summarize_line(
                "summarize.pipeline.summarization_complete",
                trace_id=trace_id,
                video_id=video_id,
                transcript_length=transcript_length,
                chunk_count=chunk_count,
                summarization_ms=summarization_ms,
                llm_provider=llm_provider,
                llm_model=llm_model,
                elapsed_ms=_ms(t0, t_after_core_llm),
            )

            key_moments = self._build_key_moments(text_chunks)
            chapters = await self._safe_chapters(text_chunks, cached_chapters=())
            dev_digest = await self._developer_digest(text_chunks, developer_mode=developer_mode)
            t_after_llm = time.perf_counter()
            llm_ms = _ms(t_llm_start, t_after_llm)

            result = normalize_final_summary(
                FinalSummary(
                    video_id=video_id,
                    title=title,
                    summary=final.summary,
                    bullets=final.bullets,
                    key_moments=key_moments,
                    transcript_length=transcript_length,
                    chunks_processed=chunk_count,
                    learning_level=learning_level,
                    suggested_questions=suggested_questions,
                    chapters=chapters,
                    developer_digest=dev_digest if developer_mode else None,
                    performance=None,
                )
            )

            digest_json: dict[str, Any] | None = None
            if result.developer_digest is not None:
                digest_json = result.developer_digest.model_dump(mode="json")

            self._cache.set(
                video_id,
                summary_type,
                learning_level,
                developer_mode,
                CachedSummaryPayload(
                    summary=result.summary,
                    bullets=tuple(result.bullets),
                    suggested_questions=tuple(result.suggested_questions),
                    chapters=tuple(c.model_dump(mode="json") for c in result.chapters),
                    developer_digest=digest_json,
                ),
            )
            total_ms = _ms(t0, time.perf_counter())
            full_perf = PipelinePerformanceMs(
                transcript_fetch_ms=transcript_fetch_ms,
                chunking_ms=chunking_ms,
                llm_ms=llm_ms,
                total_ms=total_ms,
            )
            log_summarize_line(
                "summarize.pipeline.metrics",
                trace_id=trace_id,
                video_id=video_id,
                transcript_fetch_ms=full_perf.transcript_fetch_ms,
                chunking_ms=full_perf.chunking_ms,
                llm_ms=full_perf.llm_ms,
                total_ms=full_perf.total_ms,
            )
            return result.model_copy(update={"performance": full_perf})

    async def _developer_digest(
        self,
        text_chunks: list[TranscriptTextChunk],
        *,
        developer_mode: bool,
    ) -> DeveloperStudyDigest | None:
        if not developer_mode:
            return None
        labeled = format_labeled_chunks(text_chunks)
        if len(labeled) > _MAX_LABELED_TRANSCRIPT_CHARS_FOR_DEVELOPER:
            labeled = labeled[: _MAX_LABELED_TRANSCRIPT_CHARS_FOR_DEVELOPER - 3] + "..."
        dev_user_message = build_labeled_transcript_user_message(labeled)
        try:
            return await self._llm.generate_developer_study_digest(dev_user_message)
        except (LLMInvocationError, ValueError, TypeError):
            return DeveloperStudyDigest()

    async def _safe_chapters(
        self,
        text_chunks: list[TranscriptTextChunk],
        *,
        cached_chapters: tuple[dict[str, Any], ...],
    ) -> list[VideoChapter]:
        if cached_chapters:
            try:
                return [VideoChapter.model_validate(d) for d in cached_chapters]
            except Exception:
                pass
        try:
            return await build_video_chapters(text_chunks, self._llm)
        except (LLMInvocationError, ValueError, TypeError):
            return []

    def _build_key_moments(self, text_chunks: list[TranscriptTextChunk]) -> list[KeyMoment]:
        moments: list[KeyMoment] = []
        max_note_len = 140
        for chunk in text_chunks:
            note = chunk.text.strip().replace("\n", " ")
            if len(note) > max_note_len:
                note = f"{note[:max_note_len - 3]}..."
            moments.append(
                KeyMoment(
                    time=format_seconds_hh_mm_ss(chunk.start_seconds),
                    note=note if note else "-",
                )
            )
        return moments


def build_default_summary_service(settings: Settings) -> SummaryService:
    llm = get_llm_service(settings)
    return SummaryService(settings=settings, llm=llm)


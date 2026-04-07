"""Summarize multiple videos, then merge insights with an LLM under a user topic."""

import asyncio

from pydantic import HttpUrl

from app.config import Settings
from app.exceptions import InvalidYouTubeUrlError, LLMInvocationError
from app.models.request_models import SummarizeRequest, SynthesizeRequest
from app.models.response_models import SynthesizeResponse
from app.observability.llm_request_usage import llm_request_usage_context
from app.observability.request_context import trace_context
from app.services.llm import LLMService, get_llm_service
from app.services.llm.schemas import MultiVideoSynthesisPayload
from app.services.llm.synthesize_prompting import build_multi_video_synthesis_user_message
from app.services.summary_service import SummaryService
from app.services.youtube_service import extract_video_id
from app.utils.output_normalizer import normalize_synthesize_response


def _dedupe_youtube_urls(urls: list[HttpUrl]) -> list[HttpUrl]:
    seen: set[str] = set()
    out: list[HttpUrl] = []
    for u in urls:
        vid = extract_video_id(str(u))
        if vid is None:
            raise InvalidYouTubeUrlError(f"Could not parse a valid YouTube video id from URL: {u}")
        if vid in seen:
            continue
        seen.add(vid)
        out.append(u)
    return out


def _payload_to_response(payload: MultiVideoSynthesisPayload) -> SynthesizeResponse:
    combined = payload.combined_summary.strip()
    best = payload.best_explanation.strip()
    if not combined or not best:
        raise LLMInvocationError("Synthesis returned empty combined_summary or best_explanation.")
    common = [s.strip() for s in payload.common_ideas if s and str(s).strip()]
    diff = [s.strip() for s in payload.differences if s and str(s).strip()]
    return normalize_synthesize_response(SynthesizeResponse(
        combined_summary=combined,
        common_ideas=common,
        differences=diff,
        best_explanation=best,
    ))


class SynthesizeService:
    """Runs full summarization per URL, then one structured merge call."""

    def __init__(self, summary_service: SummaryService, llm: LLMService) -> None:
        self._summary = summary_service
        self._llm = llm

    async def synthesize_from_urls(self, request: SynthesizeRequest, *, trace_id: str) -> SynthesizeResponse:
        unique_urls = _dedupe_youtube_urls(list(request.urls))
        primary_video_id = extract_video_id(str(unique_urls[0])) if unique_urls else None
        with trace_context(trace_id), llm_request_usage_context(
            endpoint="synthesize",
            video_id=primary_video_id,
        ):
            if len(unique_urls) < 2:
                raise InvalidYouTubeUrlError(
                    "Provide at least two distinct YouTube videos (duplicate URLs or ids are merged).",
                )

            summaries = await asyncio.gather(
                *[
                    self._summary.summarize_from_url(
                        SummarizeRequest(
                            url=url,
                            summary_type=request.summary_type,
                            language=request.language,
                        ),
                        trace_id=f"{trace_id}:v{i}",
                    )
                    for i, url in enumerate(unique_urls, start=1)
                ]
            )
            videos: list[tuple[int, str, str, str, list[str]]] = []
            for i, fs in enumerate(summaries, start=1):
                videos.append((i, fs.video_id, fs.title, fs.summary, list(fs.bullets)))

            user_message = build_multi_video_synthesis_user_message(topic=request.topic, videos=videos)
            payload = await self._llm.synthesize_multi_video_summaries(user_message)
            return _payload_to_response(payload)


def build_default_synthesize_service(settings: Settings) -> SynthesizeService:
    llm = get_llm_service(settings)
    summary = SummaryService(settings=settings, llm=llm)
    return SynthesizeService(summary_service=summary, llm=llm)

import asyncio

from app.config import Settings
from app.models.request_models import CompareRequest, SummarizeRequest
from app.models.response_models import CompareVideosResponse
from app.observability.llm_request_usage import llm_request_usage_context
from app.observability.request_context import trace_context
from app.services.llm import LLMService, get_llm_service
from app.services.summary_service import SummaryService
from app.services.youtube_service import extract_video_id
from app.utils.output_normalizer import normalize_compare_response


class CompareService:
    """Runs the normal summarization pipeline twice, then asks the LLM for structured similarities/differences."""

    def __init__(self, summary_service: SummaryService, llm: LLMService) -> None:
        self._summary = summary_service
        self._llm = llm

    async def compare_from_urls(self, request: CompareRequest, *, trace_id: str) -> CompareVideosResponse:
        with trace_context(trace_id), llm_request_usage_context(
            endpoint="compare",
            video_id=extract_video_id(str(request.url_1)) or extract_video_id(str(request.url_2)),
        ):
            req1 = SummarizeRequest(
                url=request.url_1,
                summary_type=request.summary_type,
                language=request.language,
            )
            req2 = SummarizeRequest(
                url=request.url_2,
                summary_type=request.summary_type,
                language=request.language,
            )
            r1, r2 = await asyncio.gather(
                self._summary.summarize_from_url(req1, trace_id=f"{trace_id}:v1"),
                self._summary.summarize_from_url(req2, trace_id=f"{trace_id}:v2"),
            )
            payload = await self._llm.compare_two_video_summaries(
                title_1=r1.title,
                summary_1=r1.summary,
                bullets_1=r1.bullets,
                title_2=r2.title,
                summary_2=r2.summary,
                bullets_2=r2.bullets,
            )
            return normalize_compare_response(CompareVideosResponse(
                summary_1=r1.summary,
                summary_2=r2.summary,
                similarities=list(payload.similarities),
                differences=list(payload.differences),
            ))


def build_default_compare_service(settings: Settings) -> CompareService:
    llm = get_llm_service(settings)
    summary = SummaryService(settings=settings, llm=llm)
    return CompareService(summary_service=summary, llm=llm)

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.exceptions import (
    InvalidYouTubeUrlError,
    LLMConfigurationError,
    LLMInvocationError,
    TranscriptFetchError,
    UnsupportedLLMProviderError,
)
from app.models.request_models import SynthesizeRequest
from app.models.response_models import SynthesizeResponse
from app.observability.summarize_pipeline import log_summarize_failure
from app.routers.error_mapping import transcript_fetch_status_code
from app.services.synthesize_service import SynthesizeService, build_default_synthesize_service
from app.services.youtube_service import extract_video_id

router = APIRouter()


def _video_id_hint(body: SynthesizeRequest) -> str | None:
    for u in body.urls:
        vid = extract_video_id(str(u))
        if vid:
            return vid
    return None


def get_synthesize_service() -> SynthesizeService:
    return build_default_synthesize_service(settings)


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize_videos(
    body: SynthesizeRequest,
    service: Annotated[SynthesizeService, Depends(get_synthesize_service)],
) -> SynthesizeResponse:
    """Summarize 2–6 distinct videos, then merge grounded insights for the given topic."""
    trace_id = str(uuid.uuid4())
    t0 = time.perf_counter()

    try:
        return await service.synthesize_from_urls(body, trace_id=trace_id)
    except InvalidYouTubeUrlError as exc:
        log_summarize_failure(
            trace_id=trace_id,
            error_stage="parse_video_id",
            error_type=type(exc).__name__,
            detail=str(exc),
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TranscriptFetchError as exc:
        log_summarize_failure(
            trace_id=trace_id,
            error_stage="transcript_fetch",
            error_type=type(exc).__name__,
            detail=str(exc),
            video_id=_video_id_hint(body),
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        raise HTTPException(transcript_fetch_status_code(str(exc)), detail=str(exc)) from exc
    except UnsupportedLLMProviderError as exc:
        log_summarize_failure(
            trace_id=trace_id,
            error_stage="llm_config",
            error_type=type(exc).__name__,
            detail=str(exc),
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
    except LLMConfigurationError as exc:
        log_summarize_failure(
            trace_id=trace_id,
            error_stage="llm_config",
            error_type=type(exc).__name__,
            detail=str(exc),
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMInvocationError as exc:
        log_summarize_failure(
            trace_id=trace_id,
            error_stage="llm_invoke",
            error_type=type(exc).__name__,
            detail=str(exc),
            video_id=_video_id_hint(body),
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.db.crud import list_recent_summaries
from app.db.session import get_db
from app.exceptions import InvalidYouTubeUrlError
from app.models.request_models import SummarizeRequest
from app.models.response_models import (
    StoredSummaryListItem,
    SummaryJobAcceptedResponse,
    SummaryJobStatusResponse,
)
from app.observability.request_tracing import request_trace_stage
from app.observability.summarize_pipeline import log_summarize_failure, log_summarize_line
from app.services.summary_job_service import SummaryJobService, build_default_summary_job_service
from app.services.youtube_service import extract_video_id

router = APIRouter()


def _video_id_hint(body: SummarizeRequest) -> str | None:
    return extract_video_id(str(body.url))


def get_summary_job_service() -> SummaryJobService:
    return build_default_summary_job_service(settings)


@router.post(
    "/summarize",
    response_model=SummaryJobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def summarize(
    body: SummarizeRequest,
    background_tasks: BackgroundTasks,
    job_service: Annotated[SummaryJobService, Depends(get_summary_job_service)],
    db: Annotated[Session, Depends(get_db)],
) -> SummaryJobAcceptedResponse:
    trace_id = str(uuid.uuid4())
    t0 = time.perf_counter()
    with request_trace_stage("summarize.parse_video_id"):
        video_id = _video_id_hint(body)
    if video_id is None:
        detail = "Could not parse a valid YouTube video id from the provided URL."
        log_summarize_failure(
            trace_id=trace_id,
            error_stage="parse_video_id",
            error_type=InvalidYouTubeUrlError.__name__,
            detail=detail,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=detail)

    try:
        with request_trace_stage("summarize.create_job"):
            response = job_service.create_job(db, body, trace_id=trace_id, video_id=video_id)
    except SQLAlchemyError as exc:
        db.rollback()
        log_summarize_failure(
            trace_id=trace_id,
            error_stage="enqueue",
            error_type=type(exc).__name__,
            detail=str(exc),
            video_id=video_id,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create summarize job: {exc}",
        ) from exc

    log_summarize_line(
        "summarize.job.queued",
        trace_id=trace_id,
        video_id=video_id,
        job_id=response.job_id,
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
    )
    background_tasks.add_task(job_service.run_job, response.job_id, body.model_dump(mode="json"))
    return response


@router.get("/status/{job_id}", response_model=SummaryJobStatusResponse)
def get_summary_status(
    job_id: str,
    job_service: Annotated[SummaryJobService, Depends(get_summary_job_service)],
    db: Annotated[Session, Depends(get_db)],
) -> SummaryJobStatusResponse:
    with request_trace_stage("summarize.status_lookup"):
        status_response = job_service.get_status(db, job_id)
    if status_response is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Summary job not found.")
    return status_response


@router.get("/summaries", response_model=list[StoredSummaryListItem])
def list_summaries(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[StoredSummaryListItem]:
    with request_trace_stage("summarize.list_recent"):
        rows = list_recent_summaries(db, limit)
    return [StoredSummaryListItem.model_validate(r) for r in rows]

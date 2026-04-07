import json
import time
import uuid
from collections.abc import Callable

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db.session import SessionLocal
from app.exceptions import (
    InvalidYouTubeUrlError,
    LLMConfigurationError,
    LLMInvocationError,
    TranscriptFetchError,
    UnsupportedLLMProviderError,
)
from app.models.request_models import SummarizeRequest
from app.models.response_models import (
    FinalSummary,
    SummaryJobAcceptedResponse,
    SummaryJobError,
    SummaryJobStatusResponse,
)
from app.observability.summarize_pipeline import log_summarize_failure, log_summarize_line
from app.repositories.summary_job_repository import SummaryJobRepository
from app.repositories.summary_repository import SummaryRepository
from app.services.summary_job_registry import get_summary_job_memory_registry
from app.services.summary_service import SummaryService, build_default_summary_service
from app.services.youtube_service import extract_video_id


class SummaryJobService:
    """Create, execute, and inspect background summarize jobs."""

    def __init__(
        self,
        settings: Settings,
        *,
        job_repository: SummaryJobRepository | None = None,
        summary_repository: SummaryRepository | None = None,
        session_factory: sessionmaker[Session] | None = None,
        summary_service_factory: Callable[[], SummaryService] | None = None,
    ) -> None:
        self._settings = settings
        self._job_repository = (
            job_repository if job_repository is not None else SummaryJobRepository()
        )
        self._summary_repository = (
            summary_repository if summary_repository is not None else SummaryRepository()
        )
        self._session_factory = session_factory if session_factory is not None else SessionLocal
        self._summary_service_factory = (
            summary_service_factory
            if summary_service_factory is not None
            else lambda: build_default_summary_service(settings)
        )

    def create_job(
        self,
        db: Session,
        request: SummarizeRequest,
        *,
        trace_id: str,
        video_id: str | None,
    ) -> SummaryJobAcceptedResponse:
        job_id = str(uuid.uuid4())
        self._job_repository.create(
            db,
            job_id=job_id,
            trace_id=trace_id,
            request=request,
            video_id=video_id,
        )
        get_summary_job_memory_registry().set_status(job_id, "queued")
        return SummaryJobAcceptedResponse(
            job_id=job_id,
            status="queued",
            status_url=f"/api/v1/status/{job_id}",
        )

    def get_status(self, db: Session, job_id: str) -> SummaryJobStatusResponse | None:
        row = self._job_repository.get(db, job_id)
        if row is None:
            return None

        result: FinalSummary | None = None
        if row.result_json:
            result = FinalSummary.model_validate(json.loads(row.result_json))

        error: SummaryJobError | None = None
        if row.error_type and row.error_detail:
            error = SummaryJobError(
                stage=row.error_stage,
                type=row.error_type,
                detail=row.error_detail,
            )

        return SummaryJobStatusResponse(
            job_id=row.job_id,
            status=row.status,
            source_url=row.source_url,
            summary_type=row.summary_type,
            language=row.language,
            video_id=row.video_id,
            summary_result_id=row.summary_result_id,
            created_at=row.created_at,
            started_at=row.started_at,
            completed_at=row.completed_at,
            result=result,
            error=error,
        )

    def recover_incomplete_jobs(self) -> int:
        with self._session_factory() as db:
            return self._job_repository.fail_incomplete(
                db,
                detail="Application restarted before the background summary job finished.",
            )

    async def run_job(self, job_id: str, request_payload: dict[str, object]) -> None:
        request = SummarizeRequest.model_validate(request_payload)

        with self._session_factory() as db:
            row = self._job_repository.get(db, job_id)
            if row is None or row.status not in ("queued", "running"):
                return
            trace_id = row.trace_id
            video_id = row.video_id or extract_video_id(str(request.url))
            self._job_repository.mark_running(db, job_id, video_id=video_id)

        get_summary_job_memory_registry().set_status(job_id, "running")
        t0 = time.perf_counter()
        try:
            result = await self._summary_service_factory().summarize_from_url(request, trace_id=trace_id)
        except InvalidYouTubeUrlError as exc:
            self._mark_failed(
                job_id=job_id,
                trace_id=trace_id,
                error_stage="parse_video_id",
                error_type=type(exc).__name__,
                detail=str(exc),
                video_id=extract_video_id(str(request.url)),
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
            return
        except TranscriptFetchError as exc:
            self._mark_failed(
                job_id=job_id,
                trace_id=trace_id,
                error_stage="transcript_fetch",
                error_type=type(exc).__name__,
                detail=str(exc),
                video_id=extract_video_id(str(request.url)),
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
            return
        except UnsupportedLLMProviderError as exc:
            self._mark_failed(
                job_id=job_id,
                trace_id=trace_id,
                error_stage="llm_config",
                error_type=type(exc).__name__,
                detail=str(exc),
                video_id=extract_video_id(str(request.url)),
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
            return
        except LLMConfigurationError as exc:
            self._mark_failed(
                job_id=job_id,
                trace_id=trace_id,
                error_stage="llm_config",
                error_type=type(exc).__name__,
                detail=str(exc),
                video_id=extract_video_id(str(request.url)),
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
            return
        except LLMInvocationError as exc:
            self._mark_failed(
                job_id=job_id,
                trace_id=trace_id,
                error_stage="llm_invoke",
                error_type=type(exc).__name__,
                detail=str(exc),
                video_id=extract_video_id(str(request.url)),
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
            return
        except Exception as exc:
            self._mark_failed(
                job_id=job_id,
                trace_id=trace_id,
                error_stage="unexpected",
                error_type=type(exc).__name__,
                detail=str(exc),
                video_id=extract_video_id(str(request.url)),
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
            return

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        try:
            with self._session_factory() as db:
                row = self._summary_repository.save(db, request, result, commit=False)
                self._job_repository.mark_completed(
                    db,
                    job_id,
                    result=result,
                    summary_result_id=row.id,
                    video_id=result.video_id,
                    commit=False,
                )
                db.commit()
        except SQLAlchemyError as exc:
            self._mark_failed(
                job_id=job_id,
                trace_id=trace_id,
                error_stage="persist",
                error_type=type(exc).__name__,
                detail=f"Summary was generated but could not be saved: {exc}",
                video_id=result.video_id,
                elapsed_ms=elapsed_ms,
            )
            return

        get_summary_job_memory_registry().set_status(job_id, "completed")
        log_summarize_line(
            "summarize.pipeline.complete",
            trace_id=trace_id,
            video_id=result.video_id,
            transcript_length=result.transcript_length,
            chunk_count=result.chunks_processed,
            elapsed_ms=elapsed_ms,
            llm_provider=self._settings.llm_provider,
            llm_model=self._settings.llm_model,
            success=True,
            persisted=True,
        )

    def _mark_failed(
        self,
        *,
        job_id: str,
        trace_id: str,
        error_stage: str,
        error_type: str,
        detail: str,
        video_id: str | None,
        elapsed_ms: float,
    ) -> None:
        get_summary_job_memory_registry().set_status(job_id, "failed")
        with self._session_factory() as db:
            self._job_repository.mark_failed(
                db,
                job_id,
                error_stage=error_stage,
                error_type=error_type,
                error_detail=detail,
                video_id=video_id,
            )
        log_summarize_failure(
            trace_id=trace_id,
            error_stage=error_stage,
            error_type=error_type,
            detail=detail,
            video_id=video_id,
            elapsed_ms=elapsed_ms,
        )


def build_default_summary_job_service(settings: Settings) -> SummaryJobService:
    return SummaryJobService(settings=settings)

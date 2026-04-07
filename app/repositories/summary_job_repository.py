import json
from datetime import datetime, timezone

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.models import SummaryJob
from app.models.request_models import SummarizeRequest
from app.models.response_models import FinalSummary


class SummaryJobRepository:
    """Persistence for async summarize jobs (``summary_jobs`` table)."""

    def create(
        self,
        db: Session,
        *,
        job_id: str,
        trace_id: str,
        request: SummarizeRequest,
        video_id: str | None,
        commit: bool = True,
    ) -> SummaryJob:
        row = SummaryJob(
            job_id=job_id,
            trace_id=trace_id,
            video_id=video_id,
            source_url=str(request.url),
            summary_type=request.summary_type,
            language=request.language,
            status="queued",
        )
        db.add(row)
        if commit:
            db.commit()
            db.refresh(row)
        else:
            db.flush()
        return row

    def get(self, db: Session, job_id: str) -> SummaryJob | None:
        return db.get(SummaryJob, job_id)

    def mark_running(
        self,
        db: Session,
        job_id: str,
        *,
        video_id: str | None = None,
        commit: bool = True,
    ) -> SummaryJob | None:
        row = self.get(db, job_id)
        if row is None:
            return None
        now = datetime.now(timezone.utc)
        row.status = "running"
        row.started_at = now
        row.updated_at = now
        if video_id is not None:
            row.video_id = video_id
        if commit:
            db.commit()
            db.refresh(row)
        else:
            db.flush()
        return row

    def mark_completed(
        self,
        db: Session,
        job_id: str,
        *,
        result: FinalSummary,
        summary_result_id: int | None,
        video_id: str | None,
        commit: bool = True,
    ) -> SummaryJob | None:
        row = self.get(db, job_id)
        if row is None:
            return None
        now = datetime.now(timezone.utc)
        row.status = "completed"
        row.video_id = video_id
        row.summary_result_id = summary_result_id
        row.result_json = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
        row.error_stage = None
        row.error_type = None
        row.error_detail = None
        row.completed_at = now
        row.updated_at = now
        if commit:
            db.commit()
            db.refresh(row)
        else:
            db.flush()
        return row

    def mark_failed(
        self,
        db: Session,
        job_id: str,
        *,
        error_stage: str,
        error_type: str,
        error_detail: str,
        video_id: str | None = None,
        commit: bool = True,
    ) -> SummaryJob | None:
        row = self.get(db, job_id)
        if row is None:
            return None
        now = datetime.now(timezone.utc)
        row.status = "failed"
        if video_id is not None:
            row.video_id = video_id
        row.result_json = None
        row.summary_result_id = None
        row.error_stage = error_stage
        row.error_type = error_type
        row.error_detail = error_detail
        row.completed_at = now
        row.updated_at = now
        if commit:
            db.commit()
            db.refresh(row)
        else:
            db.flush()
        return row

    def fail_incomplete(self, db: Session, *, detail: str) -> int:
        now = datetime.now(timezone.utc)
        stmt: Select[tuple[SummaryJob]] = select(SummaryJob).where(
            SummaryJob.status.in_(("queued", "running"))
        )
        rows = list(db.scalars(stmt).all())
        for row in rows:
            row.status = "failed"
            row.result_json = None
            row.summary_result_id = None
            row.error_stage = "background_task"
            row.error_type = "JobRecoveryError"
            row.error_detail = detail
            row.completed_at = now
            row.updated_at = now
        if rows:
            db.commit()
        return len(rows)

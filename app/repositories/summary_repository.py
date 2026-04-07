import json

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.models import SummaryResult
from app.models.request_models import SummarizeRequest
from app.models.response_models import FinalSummary


class SummaryRepository:
    """Persistence for generated summaries (``summary_results`` table)."""

    def save(
        self,
        db: Session,
        request: SummarizeRequest,
        result: FinalSummary,
        *,
        commit: bool = True,
    ) -> SummaryResult:
        row = SummaryResult(
            video_id=result.video_id,
            source_url=str(request.url),
            summary_type=request.summary_type,
            language=request.language,
            title=result.title,
            summary=result.summary,
            bullets_json=json.dumps(result.bullets, ensure_ascii=False),
            suggested_questions_json=json.dumps(result.suggested_questions, ensure_ascii=False),
            key_moments_json=json.dumps(
                [moment.model_dump() for moment in result.key_moments],
                ensure_ascii=False,
            ),
            transcript_length=result.transcript_length,
            chunks_processed=result.chunks_processed,
        )
        db.add(row)
        if commit:
            db.commit()
            db.refresh(row)
        else:
            db.flush()
        return row

    def list_recent(self, db: Session, limit: int) -> list[SummaryResult]:
        stmt: Select[tuple[SummaryResult]] = (
            select(SummaryResult).order_by(SummaryResult.created_at.desc()).limit(limit)
        )
        return list(db.scalars(stmt).all())

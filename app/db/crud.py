"""Backward-compatible summary persistence API (delegates to :class:`SummaryRepository`)."""

from sqlalchemy.orm import Session

from app.db.models import SummaryResult
from app.models.request_models import SummarizeRequest
from app.models.response_models import FinalSummary
from app.repositories.summary_repository import SummaryRepository

_summary_repo = SummaryRepository()


def save_summary(
    db: Session,
    request: SummarizeRequest,
    result: FinalSummary,
) -> SummaryResult:
    return _summary_repo.save(db, request, result)


def list_recent_summaries(db: Session, limit: int) -> list[SummaryResult]:
    return _summary_repo.list_recent(db, limit)

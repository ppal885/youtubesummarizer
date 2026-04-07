from sqlalchemy.orm import Session

from app.db.models import LLMUsageRecord


class LLMUsageRepository:
    """Persistence for aggregated per-request LLM token usage."""

    def save(
        self,
        db: Session,
        *,
        trace_id: str | None,
        video_id: str | None,
        endpoint: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        llm_call_count: int,
        cost_estimate_usd: float,
        commit: bool = True,
    ) -> LLMUsageRecord:
        row = LLMUsageRecord(
            trace_id=trace_id,
            video_id=video_id,
            endpoint=endpoint,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            llm_call_count=llm_call_count,
            cost_estimate_usd=cost_estimate_usd,
        )
        db.add(row)
        if commit:
            db.commit()
            db.refresh(row)
        else:
            db.flush()
        return row

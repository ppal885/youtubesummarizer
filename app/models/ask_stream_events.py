"""Server-sent event payloads for Q&A streaming (``POST /api/v1/ask/stream`` or ``POST /api/v1/ask`` + ``Accept: text/event-stream``)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.response_models import AskCitationSource


class AskStreamDeltaEvent(BaseModel):
    """Incremental answer text (raw composer output; final text may differ after verification)."""

    type: Literal["delta"] = "delta"
    text: str = Field(..., description="UTF-8 fragment to append in order.")


class AskStreamDoneEvent(BaseModel):
    """Final answer after grounding + citation list (same shape as non-streaming ``AskResponse``)."""

    type: Literal["done"] = "done"
    answer: str
    sources: list[AskCitationSource] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class AskStreamErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str

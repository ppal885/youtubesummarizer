"""Shared models for transcript Q&A (retrieval + LLM context)."""

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.utils.time_utils import format_seconds_hh_mm_ss


class TranscriptChunkPassage(BaseModel):
    """One searchable transcript segment, typically loaded from persistence."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., ge=0)
    chunk_index: int = Field(..., ge=0)
    start_seconds: float = Field(..., ge=0)
    text: str = Field(..., min_length=0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def time_display(self) -> str:
        return format_seconds_hh_mm_ss(self.start_seconds)

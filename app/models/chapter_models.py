"""Typed inputs for chapter detection (LLM and pipeline)."""

from pydantic import BaseModel, Field


class ChapterSegment(BaseModel):
    """One timed transcript slice passed to the chapter-labeling model."""

    start_seconds: float = Field(..., ge=0)
    text: str = Field(..., min_length=1, description="Transcript excerpt for this segment only.")

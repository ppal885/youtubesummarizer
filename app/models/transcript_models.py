from pydantic import BaseModel, Field


class TranscriptItem(BaseModel):
    start: float = Field(..., ge=0, description="Start time in seconds")
    duration: float = Field(..., ge=0, description="Caption duration in seconds")
    text: str = Field(..., min_length=0)


class TranscriptTextChunk(BaseModel):
    """A slice of merged transcript text with the approximate start time in the video."""

    text: str = Field(..., min_length=0)
    start_seconds: float = Field(..., ge=0)

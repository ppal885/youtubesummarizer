from pydantic import BaseModel, Field


class ChunkSummary(BaseModel):
    summary: str = Field(..., min_length=0)
    bullets: list[str] = Field(default_factory=list)

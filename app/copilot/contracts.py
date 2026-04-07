"""Typed contracts between copilot agents (portfolio-friendly, explicit DTOs)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TranscriptTheme(BaseModel):
    """One coarse theme or section label over a set of chunk indices."""

    theme_id: int = Field(..., ge=0)
    title: str = Field(..., min_length=1, description="Short heading, often time-anchored.")
    summary: str = Field(
        ...,
        min_length=0,
        max_length=600,
        description="Brief description of what happens in this segment (not used as evidence).",
    )
    chunk_indices: list[int] = Field(
        default_factory=list,
        description="Chunk row indices (chunk_index) covered by this theme.",
    )


class TranscriptAnalystResult(BaseModel):
    """Output of the Transcript Analyst agent."""

    ok: bool
    themes: list[TranscriptTheme] = Field(default_factory=list)
    fallback_reason: str | None = Field(
        default=None,
        description="Set when ok is False or analysis was skipped.",
    )


class ComposerResult(BaseModel):
    """Output of the Answer Composer agent."""

    ok: bool
    raw_answer: str = ""
    notes: str | None = Field(default=None, description="Error or diagnostic when ok is False.")


class VerifierResult(BaseModel):
    """Output of the Verifier agent (grounding + confidence)."""

    ok: bool = Field(..., description="False if the verifier pipeline itself failed.")
    accepted: bool = Field(
        ...,
        description="True when the answer is an explicit refusal or passes lexical grounding.",
    )
    final_answer: str = ""
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    confidence_score: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Raw lexical overlap score between the answer and retrieved evidence.",
    )
    notes: str | None = None

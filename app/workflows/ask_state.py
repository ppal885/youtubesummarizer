"""Typed LangGraph state for the YouTube transcript Q&A (copilot) workflow."""

from __future__ import annotations

import operator
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.copilot.contracts import TranscriptAnalystResult
from app.models.qa_models import TranscriptChunkPassage
from app.services.multi_hop_qa import MultiHopAssessment
from app.services.query_understanding import QueryIntent
from app.models.response_models import AskCitationSource, AskResponse
from app.models.retrieval_models import RetrievalHit
from app.models.transcript_models import TranscriptItem, TranscriptTextChunk


class CopilotAskState(BaseModel):
    """
    Mutable workflow state passed between graph nodes.

    Required conceptual fields per product spec: ``url``, ``video_id``, ``transcript``,
    ``chunks``, ``retrieved_chunks``, ``question``, ``answer``, ``sources``, ``errors``.
    Additional keys support retrieval limits, LLM raw output, and the HTTP response DTO.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    url: str = ""
    question: str = ""
    language: str = "en"

    video_id: str | None = None
    transcript: str | None = None
    transcript_items: list[TranscriptItem] = Field(
        default_factory=list,
        description="Caption lines after cleaning (typed segments).",
    )

    chunks: list[TranscriptTextChunk] = Field(default_factory=list)
    transcript_analysis: TranscriptAnalystResult | None = Field(
        default=None,
        description="Transcript Analyst output (themes / sections).",
    )
    query_intent: QueryIntent | None = Field(
        default=None,
        description="LLM or heuristic intent label (factual / conceptual / comparison / definition).",
    )
    retrieval_query: str = Field(
        default="",
        description="Rewritten query for retrieval, rerank overlap, and compression; empty means use question.",
    )
    multi_hop_assessment: MultiHopAssessment | None = Field(
        default=None,
        description="Whether to force multi-segment synthesis and timestamp citation in the answer step.",
    )
    retrieved_chunks: list[RetrievalHit] = Field(
        default_factory=list,
        description="Full ranked retrieval pool (e.g. top QA_RETRIEVAL_POOL hits after rerank, before compression).",
    )
    citation_hits: list[RetrievalHit] = Field(
        default_factory=list,
        description="Top sources for the API response (slice of synthetic hits aligned with compressed context).",
    )
    selected_passages: list[TranscriptChunkPassage] = Field(
        default_factory=list,
        description="Compressed context blocks passed to the answer LLM and lexical verifier (3–5 rows typical).",
    )
    evidence_passages_for_answer: list[TranscriptChunkPassage] = Field(
        default_factory=list,
        description="Context actually used for compose+verify; may unroll per-chunk hits when multi-hop is active.",
    )

    raw_llm_answer: str | None = Field(
        default=None,
        description="Model output before grounding post-processing.",
    )
    answer: str | None = None
    sources: list[AskCitationSource] = Field(default_factory=list)
    confidence: float | None = None
    confidence_score: float | None = None

    video_end_seconds: float = Field(0.0, ge=0)

    errors: Annotated[list[str], operator.add] = Field(default_factory=list)

    final_response: AskResponse | None = Field(
        default=None,
        description="API payload; set in ``format_response``.",
    )

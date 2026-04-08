"""
Stage 5 — Post-processing: lexical grounding / confidence and API DTO shaping.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from app.copilot.verifier_agent import VerifierAgent
from app.models.response_models import AskCitationSource, AskResponse
from app.models.retrieval_models import RetrievalHit
from app.utils.output_normalizer import normalize_ask_response, normalize_ask_source
from app.workflows.ask_state import CopilotAskState

_VERIFIER = VerifierAgent()


def hit_to_citation_source(hit: RetrievalHit) -> AskCitationSource:
    passage = hit.passage
    text = passage.text.strip().replace("\n", " ")
    max_len = 220
    if len(text) > max_len:
        text = f"{text[:max_len - 3]}..."
    return normalize_ask_source(AskCitationSource(
        start_time=passage.start_seconds,
        formatted_time=passage.time_display,
        text=text,
    ))


def validate_grounding(state: CopilotAskState, config: RunnableConfig) -> dict:
    _ = config
    if state.errors or state.raw_llm_answer is None:
        return {}
    verify_context = (
        state.evidence_passages_for_answer
        if state.evidence_passages_for_answer
        else state.selected_passages
    )
    verified = _VERIFIER.verify(
        state.raw_llm_answer,
        verify_context,
        multi_hop_assessment=state.multi_hop_assessment,
    )
    return {
        "answer": verified.final_answer,
        "confidence": verified.confidence,
        "confidence_score": verified.confidence_score,
        "sources": [hit_to_citation_source(hit) for hit in state.citation_hits],
    }


def format_response(state: CopilotAskState, config: RunnableConfig) -> dict:
    _ = config
    answer = (state.answer or "").strip()
    if not answer and state.errors:
        answer = " ".join(state.errors)
    response = normalize_ask_response(AskResponse(
        answer=answer or "",
        sources=list(state.sources),
        confidence=0.0 if state.confidence is None else float(state.confidence),
        confidence_score=0.0
        if state.confidence_score is None
        else float(state.confidence_score),
    ))
    return {"final_response": response}

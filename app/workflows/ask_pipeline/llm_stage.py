"""
Stage 4 — LLM: query understanding (retrieval query rewrite) and answer composition.

Does not run retrieval or post-verify; those are retrieval and postprocess stages.
"""

from __future__ import annotations

import time

from langchain_core.runnables import RunnableConfig

from app.copilot.answer_composer import AnswerComposerAgent
from app.services.llm.qa_grounding import rejection_answer
from app.services.multi_hop_qa import assess_multi_hop, build_answer_context_for_multi_hop
from app.services.query_understanding import merge_retrieval_query_text, run_query_understanding
from app.workflows.ask_pipeline.deps import get_ask_deps
from app.workflows.ask_state import CopilotAskState


async def query_understanding(state: CopilotAskState, config: RunnableConfig) -> dict:
    if state.errors:
        return {}
    deps = get_ask_deps(config)
    t0 = time.perf_counter()
    payload = await run_query_understanding(state.question, deps.llm)
    qu_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "query_intent": payload.intent,
        "retrieval_query": merge_retrieval_query_text(payload, fallback=state.question),
        "perf_llm_ms": qu_ms,
    }


async def compose_answer(state: CopilotAskState, config: RunnableConfig) -> dict:
    if state.errors:
        return {}
    deps = get_ask_deps(config)
    assessment = assess_multi_hop(
        state.question,
        state.selected_passages,
        state.retrieved_chunks,
        query_intent=state.query_intent,
    )
    evidence = build_answer_context_for_multi_hop(
        assessment,
        state.selected_passages,
        state.retrieved_chunks,
    )
    t0 = time.perf_counter()
    result = await AnswerComposerAgent(deps.llm).compose(
        state.question,
        evidence,
        state.transcript_analysis,
        multi_hop=assessment,
    )
    compose_ms = round((time.perf_counter() - t0) * 1000, 2)
    if not result.ok:
        return {
            "raw_llm_answer": "",
            "answer": rejection_answer(),
            "confidence": 0.0,
            "confidence_score": 0.0,
            "multi_hop_assessment": assessment,
            "evidence_passages_for_answer": evidence,
            "perf_llm_ms": compose_ms,
        }
    return {
        "raw_llm_answer": result.raw_answer,
        "multi_hop_assessment": assessment,
        "evidence_passages_for_answer": evidence,
        "perf_llm_ms": compose_ms,
    }

"""
LangGraph workflow for ``POST /api/v1/ask``.

Graph wiring only; stage logic lives in ``app.workflows.ask_pipeline`` (transcript → chunking →
LLM query understanding → retrieval → LLM compose → postprocess).
"""

from __future__ import annotations

from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app.workflows.ask_pipeline.chunking_stage import chunk_transcript, transcript_analyst
from app.workflows.ask_pipeline.deps import AskGraphDeps, get_ask_deps
from app.workflows.ask_pipeline.llm_stage import compose_answer, query_understanding
from app.workflows.ask_pipeline.postprocess_stage import (
    format_response,
    hit_to_citation_source as _hit_to_citation_source,
    validate_grounding,
)
from app.workflows.ask_pipeline.retrieval_stage import retrieve_context
from app.workflows.ask_pipeline.transcript_stage import (
    clean_transcript,
    extract_video_id,
    fetch_transcript,
    validate_input,
)
from app.workflows.ask_state import CopilotAskState

__all__ = [
    "AskGraphDeps",
    "_hit_to_citation_source",
    "build_copilot_ask_graph",
    "get_ask_deps",
    "node_answer_question",
]


def node_validate_input(state: CopilotAskState, config: RunnableConfig) -> dict:
    return validate_input(state, config)


def node_extract_video_id(state: CopilotAskState, config: RunnableConfig) -> dict:
    return extract_video_id(state, config)


def node_fetch_transcript(state: CopilotAskState, config: RunnableConfig) -> dict:
    return fetch_transcript(state, config)


def node_clean_transcript(state: CopilotAskState, config: RunnableConfig) -> dict:
    return clean_transcript(state, config)


def node_chunk_transcript(state: CopilotAskState, config: RunnableConfig) -> dict:
    return chunk_transcript(state, config)


def route_after_chunk(state: CopilotAskState) -> Literal["transcript_analyst", "format_response"]:
    if state.errors or not state.chunks:
        return "format_response"
    return "transcript_analyst"


def node_transcript_analyst(state: CopilotAskState, config: RunnableConfig) -> dict:
    return transcript_analyst(state, config)


async def node_query_understanding(state: CopilotAskState, config: RunnableConfig) -> dict:
    return await query_understanding(state, config)


async def node_retrieve_context(state: CopilotAskState, config: RunnableConfig) -> dict:
    return await retrieve_context(state, config)


def route_after_retrieve(state: CopilotAskState) -> Literal["answer_question", "format_response"]:
    if state.errors or not state.selected_passages:
        return "format_response"
    return "answer_question"


async def node_answer_question(state: CopilotAskState, config: RunnableConfig) -> dict:
    return await compose_answer(state, config)


def node_validate_grounding(state: CopilotAskState, config: RunnableConfig) -> dict:
    return validate_grounding(state, config)


def node_format_response(state: CopilotAskState, config: RunnableConfig) -> dict:
    return format_response(state, config)


def build_copilot_ask_graph() -> object:
    """Compile the copilot Q&A graph (inject ``AskGraphDeps`` per ``invoke``)."""
    graph: StateGraph = StateGraph(CopilotAskState)
    graph.add_node("validate_input", node_validate_input)
    graph.add_node("extract_video_id", node_extract_video_id)
    graph.add_node("fetch_transcript", node_fetch_transcript)
    graph.add_node("clean_transcript", node_clean_transcript)
    graph.add_node("chunk_transcript", node_chunk_transcript)
    graph.add_node("transcript_analyst", node_transcript_analyst)
    graph.add_node("query_understanding", node_query_understanding)
    graph.add_node("retrieve_context", node_retrieve_context)
    graph.add_node("answer_question", node_answer_question)
    graph.add_node("validate_grounding", node_validate_grounding)
    graph.add_node("format_response", node_format_response)

    graph.add_edge(START, "validate_input")
    graph.add_edge("validate_input", "extract_video_id")
    graph.add_edge("extract_video_id", "fetch_transcript")
    graph.add_edge("fetch_transcript", "clean_transcript")
    graph.add_edge("clean_transcript", "chunk_transcript")
    graph.add_conditional_edges(
        "chunk_transcript",
        route_after_chunk,
        {
            "transcript_analyst": "transcript_analyst",
            "format_response": "format_response",
        },
    )
    graph.add_edge("transcript_analyst", "query_understanding")
    graph.add_edge("query_understanding", "retrieve_context")
    graph.add_conditional_edges(
        "retrieve_context",
        route_after_retrieve,
        {
            "answer_question": "answer_question",
            "format_response": "format_response",
        },
    )
    graph.add_edge("answer_question", "validate_grounding")
    graph.add_edge("validate_grounding", "format_response")
    graph.add_edge("format_response", END)
    return graph.compile()

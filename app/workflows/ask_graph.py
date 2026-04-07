"""
LangGraph workflow for ``POST /api/v1/ask``.

Nodes: validate_input -> extract_video_id -> fetch_transcript -> clean_transcript ->
chunk_transcript -> (transcript_analyst | format_response) -> query_understanding -> retrieve_context ->
answer (multi-hop context expansion + composer) -> validate_grounding -> format_response.

Multi-hop: wide retrieval -> assess whether multiple segments should be combined -> if compression hides
distinct chunks, unroll top hits per ``chunk_index`` for the answer model; the original question is preserved;
the verifier uses the same evidence passages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.copilot.answer_composer import AnswerComposerAgent
from app.copilot.retrieval_agent import RetrievalAgent
from app.copilot.transcript_analyst import TranscriptAnalystAgent
from app.copilot.verifier_agent import VerifierAgent
from app.exceptions import BackendWorkflowError, EmbeddingInvocationError, InvalidYouTubeUrlError
from app.models.qa_models import TranscriptChunkPassage
from app.models.response_models import AskCitationSource, AskResponse
from app.models.retrieval_models import RetrievalHit
from app.models.transcript_models import TranscriptItem
from app.repositories.transcript_chunk_repository import TranscriptChunkRepository
from app.services.chunk_service import chunk_transcript_items
from app.services.context_compression import compress_ranked_hits, slice_citation_hits
from app.services.embeddings.factory import get_embedding_service
from app.services.llm.qa_grounding import rejection_answer
from app.services.multi_hop_qa import assess_multi_hop, build_answer_context_for_multi_hop
from app.services.query_understanding import merge_retrieval_query_text, run_query_understanding
from app.services.retrieval_service import chunk_end_times_from_items
from app.services.transcript_service import fetch_transcript_items, merge_transcript_text
from app.services.youtube_service import extract_video_id
from app.utils.output_normalizer import normalize_ask_response, normalize_ask_source
from app.utils.text_cleaner import normalize_whitespace
from app.workflows.ask_state import CopilotAskState

if TYPE_CHECKING:
    from app.config import Settings
    from app.services.llm import LLMService
    from app.services.retrieval import ChunkRetriever

_CITATION_SOURCE_LIMIT = 3

_TRANSCRIPT_ANALYST = TranscriptAnalystAgent()
_RETRIEVAL_AGENT = RetrievalAgent()
_VERIFIER_AGENT = VerifierAgent()


@dataclass(frozen=True, slots=True)
class AskGraphDeps:
    """Per-request dependencies injected via ``RunnableConfig``."""

    settings: Settings
    llm: LLMService
    retriever: ChunkRetriever
    transcript_repo: TranscriptChunkRepository
    db: Session


def _deps(config: RunnableConfig) -> AskGraphDeps:
    raw = config.get("configurable") or {}
    deps = raw.get("deps")
    if deps is None or not isinstance(deps, AskGraphDeps):
        raise BackendWorkflowError(
            "Copilot ask graph requires config['configurable']['deps'] (AskGraphDeps)."
        )
    return deps


def _hit_to_citation_source(hit: RetrievalHit) -> AskCitationSource:
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


def node_validate_input(state: CopilotAskState, config: RunnableConfig) -> dict:
    _ = config
    question = state.question.strip()
    url = state.url.strip()
    out: dict = {"question": question, "url": url}
    if not question:
        out["errors"] = ["Question must not be empty."]
    if not url:
        out["errors"] = ["URL must not be empty."]
    return out


def node_extract_video_id(state: CopilotAskState, config: RunnableConfig) -> dict:
    _ = config
    if state.errors:
        return {}
    video_id = extract_video_id(state.url)
    if video_id is None:
        raise InvalidYouTubeUrlError(
            "Could not parse a valid YouTube video id from the provided URL."
        )
    return {"video_id": video_id}


def node_fetch_transcript(state: CopilotAskState, config: RunnableConfig) -> dict:
    _ = config
    if state.errors:
        return {}
    assert state.video_id is not None
    items = fetch_transcript_items(state.video_id, state.language)
    video_end = max((item.start + item.duration) for item in items) if items else 0.0
    return {"transcript_items": items, "video_end_seconds": video_end}


def node_clean_transcript(state: CopilotAskState, config: RunnableConfig) -> dict:
    _ = config
    if state.errors:
        return {}
    cleaned = [
        TranscriptItem(start=item.start, duration=item.duration, text=normalize_whitespace(item.text))
        for item in state.transcript_items
    ]
    return {
        "transcript_items": cleaned,
        "transcript": merge_transcript_text(cleaned) or None,
    }


def node_chunk_transcript(state: CopilotAskState, config: RunnableConfig) -> dict:
    if state.errors:
        return {}
    chunks = chunk_transcript_items(state.transcript_items, _deps(config).settings)
    if not chunks:
        return {
            "chunks": [],
            "answer": "No transcript text was available to search after chunking.",
            "sources": [],
            "confidence": 0.0,
            "confidence_score": 0.0,
        }
    return {"chunks": chunks}


def route_after_chunk(state: CopilotAskState) -> Literal["transcript_analyst", "format_response"]:
    if state.errors or not state.chunks:
        return "format_response"
    return "transcript_analyst"


def node_transcript_analyst(state: CopilotAskState, config: RunnableConfig) -> dict:
    _ = config
    if state.errors:
        return {}
    return {
        "transcript_analysis": _TRANSCRIPT_ANALYST.analyze(
            merged_transcript=state.transcript,
            chunks=state.chunks,
            video_end_seconds=state.video_end_seconds,
        )
    }


async def node_query_understanding(state: CopilotAskState, config: RunnableConfig) -> dict:
    if state.errors:
        return {}
    deps = _deps(config)
    payload = await run_query_understanding(state.question, deps.llm)
    return {
        "query_intent": payload.intent,
        "retrieval_query": merge_retrieval_query_text(payload, fallback=state.question),
    }


async def node_retrieve_context(state: CopilotAskState, config: RunnableConfig) -> dict:
    if state.errors:
        return {}
    deps = _deps(config)
    settings = deps.settings
    session = deps.db
    video_id = state.video_id
    assert video_id is not None

    end_times = chunk_end_times_from_items(state.chunks, state.video_end_seconds)

    retriever_mode = settings.retriever_provider.lower().strip()
    if retriever_mode == "embedding":
        embedding_service = get_embedding_service(settings)
        try:
            vectors = embedding_service.embed([chunk.text for chunk in state.chunks])
        except EmbeddingInvocationError:
            raise
        except Exception as exc:
            raise EmbeddingInvocationError(f"Chunk embedding failed: {exc}") from exc
        deps.transcript_repo.replace_chunks_with_embeddings(
            session,
            video_id,
            state.language,
            state.chunks,
            end_times,
            vectors,
        )
    else:
        deps.transcript_repo.replace_chunks_lexical(
            session,
            video_id,
            state.language,
            state.chunks,
            end_times,
        )

    rows = deps.transcript_repo.list_chunks(session, video_id, state.language)
    passages = [TranscriptChunkPassage.model_validate(row) for row in rows]
    retrieval_query = (state.retrieval_query or "").strip() or state.question
    hits = deps.retriever.retrieve(
        retrieval_query,
        passages,
        settings.qa_retrieval_pool,
        video_end_seconds=state.video_end_seconds,
        db=session,
        video_id=video_id,
        language=state.language,
    )
    hits = _RETRIEVAL_AGENT.rerank(
        question=retrieval_query,
        hits=hits,
        analysis=state.transcript_analysis,
    )

    if not hits:
        return {
            "retrieved_chunks": [],
            "citation_hits": [],
            "selected_passages": [],
            "answer": "Not found in context: retrieval returned no passages for this question.",
            "sources": [],
            "confidence": 0.0,
            "confidence_score": 0.0,
        }

    selected, synthetic_hits = await compress_ranked_hits(
        retrieval_query,
        hits,
        settings=settings,
        llm=deps.llm,
    )
    if not selected:
        return {
            "retrieved_chunks": hits,
            "citation_hits": [],
            "selected_passages": [],
            "answer": "Not found in context: retrieval returned no passages for this question.",
            "sources": [],
            "confidence": 0.0,
            "confidence_score": 0.0,
        }

    return {
        "retrieved_chunks": hits,
        "citation_hits": slice_citation_hits(synthetic_hits, limit=_CITATION_SOURCE_LIMIT),
        "selected_passages": selected,
    }


def route_after_retrieve(state: CopilotAskState) -> Literal["answer_question", "format_response"]:
    if state.errors or not state.selected_passages:
        return "format_response"
    return "answer_question"


async def node_answer_question(state: CopilotAskState, config: RunnableConfig) -> dict:
    if state.errors:
        return {}
    deps = _deps(config)
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
    result = await AnswerComposerAgent(deps.llm).compose(
        state.question,
        evidence,
        state.transcript_analysis,
        multi_hop=assessment,
    )
    if not result.ok:
        return {
            "raw_llm_answer": "",
            "answer": rejection_answer(),
            "confidence": 0.0,
            "confidence_score": 0.0,
            "multi_hop_assessment": assessment,
            "evidence_passages_for_answer": evidence,
        }
    return {
        "raw_llm_answer": result.raw_answer,
        "multi_hop_assessment": assessment,
        "evidence_passages_for_answer": evidence,
    }


def node_validate_grounding(state: CopilotAskState, config: RunnableConfig) -> dict:
    _ = config
    if state.errors or state.raw_llm_answer is None:
        return {}
    verify_context = (
        state.evidence_passages_for_answer
        if state.evidence_passages_for_answer
        else state.selected_passages
    )
    verified = _VERIFIER_AGENT.verify(
        state.raw_llm_answer,
        verify_context,
        multi_hop_assessment=state.multi_hop_assessment,
    )
    return {
        "answer": verified.final_answer,
        "confidence": verified.confidence,
        "confidence_score": verified.confidence_score,
        "sources": [_hit_to_citation_source(hit) for hit in state.citation_hits],
    }


def node_format_response(state: CopilotAskState, config: RunnableConfig) -> dict:
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

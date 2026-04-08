"""
Stage 3 — Retrieval: persist chunks, embed (or lexical index), retrieve, rerank, compress pool to passages.

Uses ``state.retrieval_query`` (typically filled by query-understanding in the LLM stage).
Optional LLM time inside context compression is reported via ``perf_llm_ms`` delta in the patch.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from app.copilot.retrieval_agent import RetrievalAgent
from app.exceptions import EmbeddingInvocationError
from app.models.qa_models import TranscriptChunkPassage
from app.models.retrieval_models import RetrievalHit
from app.services.context_compression import compress_ranked_hits, slice_citation_hits
from app.services.embeddings.factory import get_embedding_service
from app.services.retrieval_service import chunk_end_times_from_items, ensure_transcript_chunk_embeddings
from app.workflows.ask_pipeline.deps import get_ask_deps
from app.workflows.ask_state import CopilotAskState

_CITATION_SOURCE_LIMIT = 3
_RERANKER = RetrievalAgent()


async def retrieve_context(state: CopilotAskState, config: RunnableConfig) -> dict:
    if state.errors:
        return {}
    deps = get_ask_deps(config)
    settings = deps.settings
    session = deps.db
    video_id = state.video_id
    assert video_id is not None

    end_times = chunk_end_times_from_items(state.chunks, state.video_end_seconds)

    retriever_mode = settings.retriever_provider.lower().strip()
    if retriever_mode == "embedding":
        embedding_service = get_embedding_service(settings)
        try:
            ensure_transcript_chunk_embeddings(
                session,
                deps.transcript_repo,
                embedding_service,
                settings,
                video_id,
                state.language,
                state.chunks,
                end_times,
            )
        except EmbeddingInvocationError:
            raise
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
    hits = _RERANKER.rerank(
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

    selected, synthetic_hits, compress_llm_ms = await compress_ranked_hits(
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
            "perf_llm_ms": compress_llm_ms,
        }

    return {
        "retrieved_chunks": hits,
        "citation_hits": slice_citation_hits(synthetic_hits, limit=_CITATION_SOURCE_LIMIT),
        "selected_passages": selected,
        "perf_llm_ms": compress_llm_ms,
    }

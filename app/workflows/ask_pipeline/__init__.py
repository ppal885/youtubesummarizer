"""
Ask (RAG) copilot pipeline split into independent, testable stages.

Architecture (execution order; each stage lives in its own module)::

    ┌─────────────┐    ┌────────────┐    ┌─────────────┐    ┌─────────┐    ┌────────────────┐
    │ transcript  │───▶│ chunking   │───▶│ LLM (query) │───▶│retrieval│───▶│ LLM (compose)  │
    │ validate    │    │ chunk text │    │ understand  │    │ persist │    │ answer         │
    │ fetch+clean │    │ + analyst  │    │ query       │    │ search  │    │                │
    └─────────────┘    └────────────┘    └─────────────┘    │ compress│    └───────┬────────┘
                                                              └─────────┘            │
                                                                                     ▼
                                                                            ┌────────────────┐
                                                                            │ postprocess    │
                                                                            │ verify + DTO   │
                                                                            └────────────────┘

- ``transcript_stage``: URL/question validation, video id, caption fetch, whitespace merge.
- ``chunking_stage``: transcript chunking + heuristic transcript analyst (themes for rerank).
- ``llm_stage.query_understanding``: retrieval query rewrite (LLM).
- ``retrieval_stage``: DB persist, embeddings or lexical rows, retrieve, rerank, compress pool.
- ``llm_stage.compose_answer``: multi-hop assessment + composer LLM.
- ``postprocess_stage``: lexical verifier + ``AskResponse`` normalization.

``state_merge.merge_pipeline_state`` applies patches with LangGraph-compatible additive perf keys.
``deps.AskGraphDeps`` / ``deps.get_ask_deps`` are shared across stages.
"""

from app.workflows.ask_pipeline.chunking_stage import (
    chunk_transcript,
    run_chunking_stage,
    transcript_analyst,
)
from app.workflows.ask_pipeline.deps import AskGraphDeps, get_ask_deps
from app.workflows.ask_pipeline.llm_stage import compose_answer, query_understanding
from app.workflows.ask_pipeline.postprocess_stage import format_response, validate_grounding
from app.workflows.ask_pipeline.retrieval_stage import retrieve_context
from app.workflows.ask_pipeline.state_merge import merge_pipeline_state
from app.workflows.ask_pipeline.transcript_stage import (
    clean_transcript,
    extract_video_id,
    fetch_transcript,
    run_transcript_stage,
    validate_input,
)

__all__ = [
    "AskGraphDeps",
    "chunk_transcript",
    "clean_transcript",
    "compose_answer",
    "extract_video_id",
    "fetch_transcript",
    "format_response",
    "get_ask_deps",
    "merge_pipeline_state",
    "query_understanding",
    "retrieve_context",
    "run_chunking_stage",
    "run_transcript_stage",
    "transcript_analyst",
    "validate_grounding",
    "validate_input",
]

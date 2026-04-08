"""Shared dependencies for the Ask copilot pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from langchain_core.runnables import RunnableConfig
from sqlalchemy.orm import Session

from app.exceptions import BackendWorkflowError
from app.repositories.transcript_chunk_repository import TranscriptChunkRepository

if TYPE_CHECKING:
    from app.config import Settings
    from app.services.llm import LLMService
    from app.services.retrieval import ChunkRetriever


@dataclass(frozen=True, slots=True)
class AskGraphDeps:
    """Per-request dependencies injected via ``RunnableConfig``."""

    settings: Settings
    llm: LLMService
    retriever: ChunkRetriever
    transcript_repo: TranscriptChunkRepository
    db: Session


def get_ask_deps(config: RunnableConfig) -> AskGraphDeps:
    raw = config.get("configurable") or {}
    deps = raw.get("deps")
    if deps is None or not isinstance(deps, AskGraphDeps):
        raise BackendWorkflowError(
            "Copilot ask pipeline requires config['configurable']['deps'] (AskGraphDeps)."
        )
    return deps

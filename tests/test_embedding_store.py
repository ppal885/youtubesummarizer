"""EmbeddingStore: DB + memory cache before calling the embedding provider."""

import uuid

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db import models  # noqa: F401 — register ORM mappers for Base.metadata
from app.db.base import Base
from app.db.models import TranscriptChunkRecord
from app.models.transcript_models import TranscriptTextChunk
from app.repositories.transcript_chunk_repository import TranscriptChunkRepository
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.service import EmbeddingService
from app.services.embedding_store import reset_embedding_store_for_tests
from app.services.retrieval_service import chunk_end_times_from_items, ensure_transcript_chunk_embeddings


class _CountingEmbeddings(EmbeddingProvider):
    def __init__(self, dim: int = 1536) -> None:
        self.embed_calls = 0
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls += 1
        return [[float(i % 997) / 997.0] * self._dim for i, _ in enumerate(texts)]


@pytest.fixture(autouse=True)
def _isolate_embedding_store() -> None:
    reset_embedding_store_for_tests()
    yield
    reset_embedding_store_for_tests()


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()


def _unique_vid() -> str:
    return uuid.uuid4().hex[:32]


def test_ensure_embeddings_skips_provider_when_db_already_matches(db_session: Session) -> None:
    settings = Settings(embedding_provider="mock", retriever_provider="embedding")
    provider = _CountingEmbeddings()
    service = EmbeddingService(provider, batch_size=64)
    repo = TranscriptChunkRepository()
    chunks = [TranscriptTextChunk(text="hello world", start_seconds=0.0)]
    ends = chunk_end_times_from_items(chunks, video_end_seconds=120.0)
    video_id = _unique_vid()

    db = db_session
    ensure_transcript_chunk_embeddings(
        db, repo, service, settings, video_id, "en", chunks, ends
    )
    assert provider.embed_calls == 1

    ensure_transcript_chunk_embeddings(
        db, repo, service, settings, video_id, "en", chunks, ends
    )
    assert provider.embed_calls == 1


def test_ensure_embeddings_recomputes_when_chunk_text_changes(db_session: Session) -> None:
    settings = Settings(embedding_provider="mock", retriever_provider="embedding")
    provider = _CountingEmbeddings()
    service = EmbeddingService(provider, batch_size=64)
    repo = TranscriptChunkRepository()
    video_id = _unique_vid()
    db = db_session

    chunks_a = [TranscriptTextChunk(text="alpha", start_seconds=0.0)]
    ends_a = chunk_end_times_from_items(chunks_a, video_end_seconds=60.0)
    ensure_transcript_chunk_embeddings(
        db, repo, service, settings, video_id, "en", chunks_a, ends_a
    )
    assert provider.embed_calls == 1

    chunks_b = [TranscriptTextChunk(text="beta", start_seconds=0.0)]
    ends_b = chunk_end_times_from_items(chunks_b, video_end_seconds=60.0)
    ensure_transcript_chunk_embeddings(
        db, repo, service, settings, video_id, "en", chunks_b, ends_b
    )
    assert provider.embed_calls == 2


def test_ensure_embeddings_uses_memory_when_db_cleared_same_process(db_session: Session) -> None:
    settings = Settings(embedding_provider="mock", retriever_provider="embedding")
    provider = _CountingEmbeddings()
    service = EmbeddingService(provider, batch_size=64)
    repo = TranscriptChunkRepository()
    chunks = [TranscriptTextChunk(text="cached row", start_seconds=1.0)]
    ends = chunk_end_times_from_items(chunks, video_end_seconds=90.0)
    video_id = _unique_vid()

    db = db_session
    ensure_transcript_chunk_embeddings(
        db, repo, service, settings, video_id, "en", chunks, ends
    )
    assert provider.embed_calls == 1

    db.execute(delete(TranscriptChunkRecord).where(TranscriptChunkRecord.video_id == video_id))
    db.commit()

    ensure_transcript_chunk_embeddings(
        db, repo, service, settings, video_id, "en", chunks, ends
    )
    assert provider.embed_calls == 1
    rows = repo.list_chunks(db, video_id, "en")
    assert len(rows) == 1 and rows[0].embedding is not None

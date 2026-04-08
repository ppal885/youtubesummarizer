"""Cache-first persistence for per-video transcript chunk embeddings (Ask / pgvector path)."""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from typing import TYPE_CHECKING

from app.config import Settings
from app.exceptions import EmbeddingInvocationError
from app.models.transcript_models import TranscriptTextChunk

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.db.models import TranscriptChunkRecord
    from app.repositories.transcript_chunk_repository import TranscriptChunkRepository
    from app.services.embeddings.service import EmbeddingService


def chunk_content_fingerprint(
    language: str,
    chunks: list[TranscriptTextChunk],
    *,
    embedding_provider: str,
    embedding_model: str,
    embedding_dimensions: int,
) -> str:
    """Stable hash of chunk layout + text + embedding config (invalidates cache when any change)."""
    payload = {
        "language": language,
        "provider": embedding_provider.lower().strip(),
        "model": embedding_model.strip(),
        "dim": embedding_dimensions,
        "chunks": [(round(ch.start_seconds, 6), ch.text) for ch in chunks],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _rows_match_chunks_with_embeddings(
    rows: list[TranscriptChunkRecord],
    chunks: list[TranscriptTextChunk],
    *,
    expected_dim: int,
) -> bool:
    if len(rows) != len(chunks):
        return False
    by_idx = {r.chunk_index: r for r in rows}
    if len(by_idx) != len(rows):
        return False
    for i, ch in enumerate(chunks):
        r = by_idx.get(i)
        if r is None:
            return False
        if r.text != ch.text or r.start_time != ch.start_seconds:
            return False
        emb = r.embedding
        if emb is None or len(emb) != expected_dim:
            return False
    return True


class EmbeddingStore:
    """DB-backed embedding cache with an in-process LRU for repeated access."""

    def __init__(self, max_entries: int = 256) -> None:
        self._max_entries = max_entries
        self._mem: OrderedDict[tuple[str, str], list[list[float]]] = OrderedDict()

    def clear(self) -> None:
        self._mem.clear()

    def _touch(self, key: tuple[str, str], vectors: list[list[float]]) -> None:
        self._mem[key] = [list(v) for v in vectors]
        self._mem.move_to_end(key)
        while len(self._mem) > self._max_entries:
            self._mem.popitem(last=False)

    def ensure_persisted(
        self,
        db: Session,
        repo: TranscriptChunkRepository,
        embedding_service: EmbeddingService,
        settings: Settings,
        video_id: str,
        language: str,
        chunks: list[TranscriptTextChunk],
        end_times: list[float | None],
    ) -> None:
        expected_dim = embedding_service.dimension
        fp = chunk_content_fingerprint(
            language,
            chunks,
            embedding_provider=settings.embedding_provider,
            embedding_model=settings.embedding_model,
            embedding_dimensions=expected_dim,
        )
        cache_key = (video_id, fp)

        rows = repo.list_chunks(db, video_id, language)
        if _rows_match_chunks_with_embeddings(rows, chunks, expected_dim=expected_dim):
            self._touch(cache_key, [list(r.embedding or []) for r in rows])
            return

        cached = self._mem.get(cache_key)
        if cached is not None and len(cached) == len(chunks):
            repo.replace_chunks_with_embeddings(db, video_id, language, chunks, end_times, cached)
            self._touch(cache_key, cached)
            return

        try:
            texts = [c.text for c in chunks]
            vectors = [vec for _, vec in embedding_service.embed_paired(texts)]
        except EmbeddingInvocationError:
            raise
        except Exception as exc:
            raise EmbeddingInvocationError(f"Chunk embedding failed: {exc}") from exc

        repo.replace_chunks_with_embeddings(db, video_id, language, chunks, end_times, vectors)
        self._touch(cache_key, vectors)


_store: EmbeddingStore | None = None


def get_embedding_store() -> EmbeddingStore:
    global _store
    if _store is None:
        _store = EmbeddingStore()
    return _store


def reset_embedding_store_for_tests() -> None:
    """Clear in-process vectors (pytest isolation)."""
    global _store
    if _store is not None:
        _store.clear()

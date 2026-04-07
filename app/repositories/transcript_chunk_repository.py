"""Persistence for per-video transcript slices used in Q&A (lexical + embedding paths)."""

from __future__ import annotations

import math

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.db.constants import VECTOR_STORAGE_DIMENSIONS
from app.db.models import TranscriptChunkRecord
from app.models.qa_models import TranscriptChunkPassage
from app.models.transcript_models import TranscriptTextChunk


def _cosine_distance(a: list[float], b: list[float]) -> float:
    """Cosine distance in [0, 2] (consistent with pgvector ``<=>`` on unit vectors)."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 2.0
    cos_sim = dot / (na * nb)
    cos_sim = max(-1.0, min(1.0, cos_sim))
    return 1.0 - cos_sim


class TranscriptChunkRepository:
    """Replace-all chunk rows for a (video_id, language) and support hybrid retrieval."""

    def replace_chunks_lexical(
        self,
        db: Session,
        video_id: str,
        language: str,
        text_chunks: list[TranscriptTextChunk],
        end_times: list[float | None],
    ) -> None:
        if len(end_times) != len(text_chunks):
            raise ValueError("end_times must align with text_chunks")
        db.execute(
            delete(TranscriptChunkRecord).where(
                TranscriptChunkRecord.video_id == video_id,
                TranscriptChunkRecord.language == language,
            )
        )
        for idx, (ch, end_t) in enumerate(zip(text_chunks, end_times, strict=True)):
            db.add(
                TranscriptChunkRecord(
                    video_id=video_id,
                    language=language,
                    chunk_index=idx,
                    text=ch.text,
                    start_time=ch.start_seconds,
                    end_time=end_t,
                    embedding=None,
                )
            )
        db.commit()

    def replace_chunks_with_embeddings(
        self,
        db: Session,
        video_id: str,
        language: str,
        text_chunks: list[TranscriptTextChunk],
        end_times: list[float | None],
        vectors: list[list[float]],
    ) -> None:
        if len(vectors) != len(text_chunks) or len(end_times) != len(text_chunks):
            raise ValueError("vectors and end_times must match text_chunks length")
        db.execute(
            delete(TranscriptChunkRecord).where(
                TranscriptChunkRecord.video_id == video_id,
                TranscriptChunkRecord.language == language,
            )
        )
        for idx, (ch, end_t, vec) in enumerate(zip(text_chunks, end_times, vectors, strict=True)):
            db.add(
                TranscriptChunkRecord(
                    video_id=video_id,
                    language=language,
                    chunk_index=idx,
                    text=ch.text,
                    start_time=ch.start_seconds,
                    end_time=end_t,
                    embedding=list(vec),
                )
            )
        db.commit()

    def list_chunks(self, db: Session, video_id: str, language: str) -> list[TranscriptChunkRecord]:
        stmt = (
            select(TranscriptChunkRecord)
            .where(
                TranscriptChunkRecord.video_id == video_id,
                TranscriptChunkRecord.language == language,
            )
            .order_by(TranscriptChunkRecord.chunk_index.asc())
        )
        return list(db.scalars(stmt).all())

    def search_similar_with_cosine_distance(
        self,
        db: Session,
        video_id: str,
        language: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[tuple[TranscriptChunkPassage, float]]:
        """Return (passage, cosine_distance) pairs ordered by distance ascending."""
        if limit <= 0:
            return []
        dialect = db.get_bind().dialect.name
        if dialect == "postgresql":
            return self._pg_cosine(db, video_id, language, query_embedding, limit)
        return self._sqlite_cosine(db, video_id, language, query_embedding, limit)

    def _sqlite_cosine(
        self,
        db: Session,
        video_id: str,
        language: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[tuple[TranscriptChunkPassage, float]]:
        rows = [r for r in self.list_chunks(db, video_id, language) if r.embedding is not None]
        scored: list[tuple[TranscriptChunkRecord, float]] = []
        for r in rows:
            emb = r.embedding or []
            dist = _cosine_distance(query_embedding, emb)
            scored.append((r, dist))
        scored.sort(key=lambda x: x[1])
        out: list[tuple[TranscriptChunkPassage, float]] = []
        for r, dist in scored[:limit]:
            out.append((TranscriptChunkPassage.model_validate(r), dist))
        return out

    def _pg_cosine(
        self,
        db: Session,
        video_id: str,
        language: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[tuple[TranscriptChunkPassage, float]]:
        dim = VECTOR_STORAGE_DIMENSIONS
        if len(query_embedding) != dim:
            raise ValueError(f"Query embedding dim {len(query_embedding)} != expected {dim}")
        vec_literal = "[" + ",".join(f"{x:.8g}" for x in query_embedding) + "]"
        sql = text(
            f"""
            SELECT id,
                   (embedding <=> CAST(:qv AS vector({dim}))) AS dist
            FROM transcript_chunks
            WHERE video_id = :vid AND language = :lang AND embedding IS NOT NULL
            ORDER BY dist ASC
            LIMIT :lim
            """
        )
        pairs = list(db.execute(sql, {"qv": vec_literal, "vid": video_id, "lang": language, "lim": limit}))
        if not pairs:
            return []
        id_list = [int(p[0]) for p in pairs]
        dist_map = {int(p[0]): float(p[1]) for p in pairs}
        stmt = select(TranscriptChunkRecord).where(TranscriptChunkRecord.id.in_(id_list))
        records = {r.id: r for r in db.scalars(stmt).all()}
        out: list[tuple[TranscriptChunkPassage, float]] = []
        for chunk_id in id_list:
            r = records.get(chunk_id)
            if r is None:
                continue
            out.append((TranscriptChunkPassage.model_validate(r), dist_map[chunk_id]))
        return out

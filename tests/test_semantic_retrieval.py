import pytest

from app.models.qa_models import TranscriptChunkPassage
from app.models.transcript_models import TranscriptTextChunk
from app.services.retrieval.embedding_retriever import EmbeddingChunkRetriever
from app.services.retrieval_service import chunk_end_times_from_items, passages_to_transcript_chunks
from app.config import Settings


def test_passages_to_transcript_chunks_end_times() -> None:
    passages = [
        TranscriptChunkPassage(id=1, chunk_index=0, start_seconds=0.0, text="a"),
        TranscriptChunkPassage(id=2, chunk_index=1, start_seconds=10.0, text="b"),
    ]
    chunks = passages_to_transcript_chunks(passages, video_end_seconds=99.0)
    assert len(chunks) == 2
    assert chunks[0].end_time == 10.0
    assert chunks[1].end_time == 99.0


def test_chunk_end_times_from_items() -> None:
    chunks = [
        TranscriptTextChunk(text="a", start_seconds=0.0),
        TranscriptTextChunk(text="b", start_seconds=5.0),
    ]
    ends = chunk_end_times_from_items(chunks, video_end_seconds=100.0)
    assert ends == [5.0, 100.0]


def test_embedding_retriever_requires_db_kwargs() -> None:
    settings = Settings(retriever_provider="embedding", embedding_provider="mock")
    r = EmbeddingChunkRetriever(settings)
    with pytest.raises(ValueError, match="db="):
        r.retrieve("q", [], top_k=2)

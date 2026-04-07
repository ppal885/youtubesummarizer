from app.models.qa_models import TranscriptChunkPassage
from app.services.retrieval.mock_retriever import MockChunkRetriever


def test_mock_retriever_prefers_keyword_overlap() -> None:
    r = MockChunkRetriever()
    passages = [
        TranscriptChunkPassage(id=1, chunk_index=0, start_seconds=0, text="cats and dogs"),
        TranscriptChunkPassage(id=2, chunk_index=1, start_seconds=10, text="vector databases are fast"),
        TranscriptChunkPassage(id=3, chunk_index=2, start_seconds=20, text="unrelated cooking tips"),
    ]
    out = r.retrieve("Tell me about vector databases", passages, top_k=2)
    assert len(out) == 2
    assert out[0].passage.chunk_index == 1
    assert out[0].keyword_score >= 0
    assert "kw(" in out[0].ranking_explanation

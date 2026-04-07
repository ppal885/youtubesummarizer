from app.evaluation.metrics import (
    chunk_coverage_score,
    lexical_support_ratio,
    retrieval_relevance_score,
)
from app.models.qa_models import TranscriptChunkPassage
from app.models.retrieval_models import RetrievalHit


def test_lexical_support_ratio_full_overlap() -> None:
    assert lexical_support_ratio("hello world test", "hello world test extra") == 1.0


def test_lexical_support_ratio_partial() -> None:
    r = lexical_support_ratio("alpha beta gamma", "alpha beta only")
    assert 0.5 < r < 1.0


def test_chunk_coverage_score() -> None:
    hits = [
        RetrievalHit(
            passage=TranscriptChunkPassage(
                id=1,
                chunk_index=0,
                start_seconds=0.0,
                text="a",
            ),
            semantic_score=0.5,
            keyword_score=0.5,
            final_score=0.5,
            ranking_explanation="x",
        ),
        RetrievalHit(
            passage=TranscriptChunkPassage(
                id=2,
                chunk_index=2,
                start_seconds=10.0,
                text="b",
            ),
            semantic_score=0.5,
            keyword_score=0.5,
            final_score=0.5,
            ranking_explanation="y",
        ),
    ]
    assert chunk_coverage_score(hits, total_chunks=10) == 0.2


def test_retrieval_relevance_score_empty() -> None:
    assert retrieval_relevance_score("what is this", []) == 0.0

from app.models.qa_models import TranscriptChunkPassage
from app.services.retrieval.hybrid_rank import rank_hybrid
from app.services.retrieval.keyword_bm25 import bm25_scores_normalized, cosine_distance_to_similarity, tokenize


def test_cosine_distance_to_similarity_endpoints() -> None:
    assert cosine_distance_to_similarity(0.0) == 1.0
    assert cosine_distance_to_similarity(2.0) == 0.0


def test_bm25_prefers_matching_terms() -> None:
    passages = [
        TranscriptChunkPassage(id=1, chunk_index=0, start_seconds=0.0, text="cats and dogs"),
        TranscriptChunkPassage(id=2, chunk_index=1, start_seconds=1.0, text="postgres vector search tutorial"),
    ]
    scores = bm25_scores_normalized("postgres vector", passages)
    assert scores[2] > scores[1]


def test_rank_hybrid_prefers_both_signals() -> None:
    corpus = [
        TranscriptChunkPassage(id=1, chunk_index=0, start_seconds=0.0, text="alpha only"),
        TranscriptChunkPassage(id=2, chunk_index=1, start_seconds=1.0, text="beta keyword match"),
        TranscriptChunkPassage(id=3, chunk_index=2, start_seconds=2.0, text="beta keyword match extra"),
    ]
    # Chunk 2: best semantic (distance 0); chunk 3: same keyword as 2 but worse semantic
    semantic_hits = [
        (corpus[1], 0.0),
        (corpus[2], 1.5),
        (corpus[0], 1.99),
    ]
    hits = rank_hybrid(
        question="beta keyword",
        corpus=corpus,
        semantic_hits=semantic_hits,
        top_k=2,
        alpha=0.5,
        beta=0.5,
    )
    assert len(hits) == 2
    assert hits[0].passage.id == 2
    assert "sem(" in hits[0].ranking_explanation and "kw(" in hits[0].ranking_explanation


def test_tokenize_strips_punctuation() -> None:
    assert "hello" in tokenize("Hello, world!")

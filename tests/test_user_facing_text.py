from app.copilot.transcript_analyst import TranscriptAnalystAgent
from app.models.retrieval_models import RetrievalHit
from app.models.transcript_models import TranscriptTextChunk
from app.models.qa_models import TranscriptChunkPassage
from app.services.context_compression import compress_heuristic
from app.workflows.ask_graph import _hit_to_citation_source


def test_transcript_analyst_uses_ascii_ellipsis() -> None:
    agent = TranscriptAnalystAgent()
    chunks = [
        TranscriptTextChunk(start_seconds=0.0, text="x" * 220),
        TranscriptTextChunk(start_seconds=30.0, text="y" * 220),
    ]
    result = agent.analyze(
        merged_transcript=" ".join(chunk.text for chunk in chunks),
        chunks=chunks,
        video_end_seconds=60.0,
    )

    assert result.ok is True
    assert result.themes
    assert "..." in result.themes[0].summary
    assert "â" not in result.themes[0].summary


def test_context_compression_uses_ascii_range_separator() -> None:
    hits = [
        RetrievalHit(
            passage=TranscriptChunkPassage(
                id=1,
                chunk_index=0,
                start_seconds=12.0,
                text="A" * 400,
            ),
            semantic_score=0.8,
            keyword_score=0.7,
            final_score=0.75,
            ranking_explanation="unit-test",
        ),
        RetrievalHit(
            passage=TranscriptChunkPassage(
                id=2,
                chunk_index=1,
                start_seconds=18.0,
                text="B" * 400,
            ),
            semantic_score=0.7,
            keyword_score=0.8,
            final_score=0.76,
            ranking_explanation="unit-test",
        ),
    ]
    passages, _ = compress_heuristic(hits, 1)

    assert passages
    assert "(00:12-00:18)" in passages[0].text
    assert "â" not in passages[0].text


def test_citation_truncation_uses_ascii_ellipsis() -> None:
    hit = RetrievalHit(
        passage=TranscriptChunkPassage(
            id=1,
            chunk_index=0,
            start_seconds=15.0,
            text="z" * 300,
        ),
        semantic_score=0.8,
        keyword_score=0.8,
        final_score=0.8,
        ranking_explanation="unit-test",
    )

    source = _hit_to_citation_source(hit)
    assert source.text.endswith("...")
    assert "â" not in source.text

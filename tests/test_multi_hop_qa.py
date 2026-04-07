"""Unit tests for multi-hop assessment and per-chunk context unrolling."""

from app.models.qa_models import TranscriptChunkPassage
from app.models.retrieval_models import RetrievalHit
from app.services.multi_hop_qa import (
    MultiHopAssessment,
    assess_multi_hop,
    build_answer_context_for_multi_hop,
)


def _hit(chunk_index: int, start: float, text: str) -> RetrievalHit:
    p = TranscriptChunkPassage(id=chunk_index, chunk_index=chunk_index, start_seconds=start, text=text)
    return RetrievalHit(
        passage=p,
        semantic_score=0.5,
        keyword_score=0.5,
        final_score=0.5,
        ranking_explanation="test",
    )


def test_assess_multi_hop_triggers_for_comparison_intent_with_two_chunks() -> None:
    hits = [_hit(0, 0.0, "alpha"), _hit(1, 60.0, "beta")]
    compressed = [
        TranscriptChunkPassage(id=0, chunk_index=0, start_seconds=0.0, text="alpha beta merged"),
    ]
    a = assess_multi_hop("How do these differ?", compressed, hits, query_intent="comparison")
    assert a.requires_multi_source is True
    assert a.distinct_evidence_segments == 2


def test_build_answer_context_unrolls_when_multi_hop_and_single_compressed_block() -> None:
    hits = [
        _hit(0, 0.0, "First segment content here."),
        _hit(1, 120.0, "Second segment other facts."),
    ]
    compressed = [
        TranscriptChunkPassage(id=0, chunk_index=0, start_seconds=0.0, text="merged blob"),
    ]
    assessment = MultiHopAssessment(
        requires_multi_source=True,
        distinct_evidence_segments=2,
        synthesis_instruction="x",
    )
    out = build_answer_context_for_multi_hop(assessment, compressed, hits)
    assert len(out) == 2
    assert {p.chunk_index for p in out} == {0, 1}
    by_idx = {p.chunk_index: p for p in out}
    assert "First segment" in by_idx[0].text
    assert "Second segment" in by_idx[1].text


def test_build_answer_context_keeps_compressed_when_already_multi_chunk() -> None:
    hits = [_hit(0, 0.0, "a"), _hit(1, 10.0, "b")]
    compressed = [
        TranscriptChunkPassage(id=0, chunk_index=0, start_seconds=0.0, text="block0"),
        TranscriptChunkPassage(id=1, chunk_index=1, start_seconds=10.0, text="block1"),
    ]
    assessment = MultiHopAssessment(
        requires_multi_source=True,
        distinct_evidence_segments=2,
        synthesis_instruction="x",
    )
    out = build_answer_context_for_multi_hop(assessment, compressed, hits)
    assert out == compressed

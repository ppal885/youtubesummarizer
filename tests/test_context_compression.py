from app.models.qa_models import TranscriptChunkPassage
from app.models.retrieval_models import RetrievalHit
from app.services.context_compression import (
    compress_heuristic,
    heuristic_compressed_payload,
    map_llm_payload_to_context,
    slice_citation_hits,
)


def _hit(idx: int, start: float, text: str) -> RetrievalHit:
    p = TranscriptChunkPassage(id=idx + 1, chunk_index=idx, start_seconds=start, text=text)
    return RetrievalHit(
        passage=p,
        semantic_score=0.5,
        keyword_score=0.5,
        final_score=0.5,
        ranking_explanation="test",
    )


def test_compress_heuristic_merges_to_target_groups() -> None:
    hits = [_hit(i, float(i * 10), f"line {i} " * 20) for i in range(10)]
    passages, synth = compress_heuristic(hits, target=4)
    assert len(passages) == len(synth) == 4
    assert all("(" in p.text and ")" in p.text for p in passages)
    assert passages[0].start_seconds <= passages[1].start_seconds


def test_compress_heuristic_pass_through_when_small_pool() -> None:
    hits = [_hit(0, 0.0, "a"), _hit(1, 5.0, "b")]
    passages, synth = compress_heuristic(hits, target=4)
    assert len(passages) == 2
    assert synth[0].passage.chunk_index == 0


def test_heuristic_payload_round_trip_mapping() -> None:
    hits = [_hit(i, float(i * 10), f"chunk {i}") for i in range(8)]
    payload = heuristic_compressed_payload(hits, 4)
    mapped = map_llm_payload_to_context(payload, hits, target=4)
    assert mapped is not None
    passages, synth = mapped
    assert len(passages) == 4
    assert len(synth) == 4


def test_slice_citation_hits() -> None:
    h = _hit(0, 0.0, "x")
    assert len(slice_citation_hits([h, h, h, h], limit=3)) == 3

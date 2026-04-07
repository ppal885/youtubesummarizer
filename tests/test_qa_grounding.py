from app.models.qa_models import TranscriptChunkPassage
from app.services.llm.qa_grounding import (
    NOT_MENTIONED_PHRASE,
    evaluate_qa_answer,
    postprocess_qa_answer,
)


def _p(start: float, text: str, idx: int = 0) -> TranscriptChunkPassage:
    return TranscriptChunkPassage(id=idx + 1, chunk_index=idx, start_seconds=start, text=text)


def test_postprocess_explicit_not_mentioned_normalizes_and_zero_confidence() -> None:
    passages = [_p(0, "the speaker discusses neural networks")]
    ans, conf = postprocess_qa_answer("  not mentioned in the video  ", passages)
    assert ans == NOT_MENTIONED_PHRASE
    assert conf == 0.0


def test_postprocess_ungrounded_replaces_with_refusal() -> None:
    passages = [_p(10, "only about cooking pasta")]
    ans, conf = postprocess_qa_answer(
        "The video explains quantum field theory in depth with equations.",
        passages,
    )
    assert ans == NOT_MENTIONED_PHRASE
    assert conf == 0.0


def test_postprocess_grounded_keeps_answer_and_positive_confidence() -> None:
    passages = [_p(66, "We use retrieval augmented generation for citations.")]
    ans, conf = postprocess_qa_answer(
        "The speaker mentions retrieval augmented generation for citations.",
        passages,
    )
    assert "retrieval" in ans.lower()
    assert 0.35 <= conf <= 1.0


def test_evaluate_qa_answer_marks_low_overlap_as_low_confidence() -> None:
    passages = [_p(14, "Redis is used as a cache for fast reads and writes.")]
    result = evaluate_qa_answer(
        "Redis is a cache, but the speaker also explains kubernetes autoscaling service meshes tracing postgres sharding and graphql federation.",
        passages,
    )

    assert result.final_answer.startswith("Redis is a cache")
    assert result.accepted is True
    assert result.low_confidence is True
    assert 0.08 <= result.confidence_score < 0.22
    assert result.confidence == result.confidence_score


def test_evaluate_qa_answer_rejects_very_low_overlap() -> None:
    passages = [_p(10, "This segment is only about cooking pasta.")]
    result = evaluate_qa_answer(
        "The video explains quantum field theory with equations and particle collisions.",
        passages,
    )

    assert result.final_answer == NOT_MENTIONED_PHRASE
    assert result.accepted is False
    assert result.low_confidence is False
    assert result.confidence == 0.0

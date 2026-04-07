"""Verifier agent: lexical grounding, confidence, and safe fallback on failure."""

from __future__ import annotations

from app.copilot.contracts import VerifierResult
from app.models.qa_models import TranscriptChunkPassage
from app.services.llm.qa_grounding import (
    NOT_MENTIONED_PHRASE,
    evaluate_qa_answer,
    rejection_answer,
)
from app.services.multi_hop_qa import MultiHopAssessment, adjust_confidence_for_multi_hop


class VerifierAgent:
    """Validates that the composed answer is supported by retrieved evidence."""

    def verify(
        self,
        raw_answer: str,
        passages: list[TranscriptChunkPassage],
        *,
        multi_hop_assessment: MultiHopAssessment | None = None,
    ) -> VerifierResult:
        try:
            stripped = raw_answer.strip()
            if not stripped:
                return VerifierResult(
                    ok=True,
                    accepted=False,
                    final_answer=rejection_answer(),
                    confidence=0.0,
                    confidence_score=0.0,
                    notes="empty_composer_output",
                )
            grounding = evaluate_qa_answer(stripped, passages)
            answer = grounding.final_answer
            conf = grounding.confidence
            conf = adjust_confidence_for_multi_hop(
                answer,
                passages,
                conf,
                multi_hop_assessment,
            )
            accepted = grounding.accepted or answer == NOT_MENTIONED_PHRASE
            return VerifierResult(
                ok=True,
                accepted=accepted,
                final_answer=answer,
                confidence=conf,
                confidence_score=grounding.confidence_score,
                notes=grounding.notes,
            )
        except Exception as exc:
            return VerifierResult(
                ok=False,
                accepted=False,
                final_answer=rejection_answer(),
                confidence=0.0,
                confidence_score=0.0,
                notes=str(exc),
            )

"""Answer Composer agent: calls the LLM with optional thematic orientation."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.copilot.contracts import ComposerResult, TranscriptAnalystResult
from app.models.qa_models import TranscriptChunkPassage
from app.services.llm import LLMService
from app.services.multi_hop_qa import MultiHopAssessment


class AnswerComposerAgent:
    """Produces a raw model answer grounded in retrieved passages."""

    def __init__(self, llm: LLMService) -> None:
        self._llm = llm

    async def compose(
        self,
        question: str,
        passages: list[TranscriptChunkPassage],
        analysis: TranscriptAnalystResult | None,
        *,
        multi_hop: MultiHopAssessment | None = None,
    ) -> ComposerResult:
        try:
            response = await self._llm.answer_question(
                question,
                passages,
                orientation_notes=self._orientation_notes(analysis),
                evidence_synthesis_notes=self._evidence_notes(multi_hop),
            )
            return ComposerResult(ok=True, raw_answer=response.answer.strip(), notes=None)
        except Exception as exc:
            return ComposerResult(ok=False, raw_answer="", notes=str(exc))

    async def compose_stream(
        self,
        question: str,
        passages: list[TranscriptChunkPassage],
        analysis: TranscriptAnalystResult | None,
        *,
        multi_hop: MultiHopAssessment | None = None,
    ) -> AsyncIterator[str]:
        """Stream plain-text tokens with the same prompt shaping as ``compose``."""
        async for fragment in self._llm.answer_question_stream(
            question,
            passages,
            orientation_notes=self._orientation_notes(analysis),
            evidence_synthesis_notes=self._evidence_notes(multi_hop),
        ):
            yield fragment

    def _orientation_notes(self, analysis: TranscriptAnalystResult | None) -> str | None:
        if analysis is None or not analysis.ok or not analysis.themes:
            return None
        lines = [
            "Thematic outline (orientation only - cite CONTEXT, not this outline):",
        ]
        for theme in analysis.themes[:6]:
            lines.append(f"- {theme.title}: {theme.summary}")
        return "\n".join(lines)

    def _evidence_notes(self, multi_hop: MultiHopAssessment | None) -> str | None:
        if multi_hop is None:
            return None
        text = multi_hop.synthesis_instruction.strip()
        return text or None

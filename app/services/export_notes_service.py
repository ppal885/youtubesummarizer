"""Orchestrate summary + learning flows into a single markdown export."""

import asyncio
import uuid

from app.config import Settings
from app.models.request_models import ExportNotesRequest, SummarizeRequest, TranscriptLearningRequest
from app.models.response_models import ExportNotesResponse
from app.services.export_notes_markdown import build_notes_export_markdown, suggest_export_filename
from app.services.learning_service import LearningService, build_default_learning_service
from app.services.summary_service import SummaryService, build_default_summary_service


class ExportNotesService:
    """Compose ``SummaryService`` + ``LearningService`` without duplicating transcript logic."""

    def __init__(self, summary: SummaryService, learning: LearningService) -> None:
        self._summary = summary
        self._learning = learning

    async def export_markdown(self, request: ExportNotesRequest) -> ExportNotesResponse:
        trace_id = str(uuid.uuid4())
        summarize_body = SummarizeRequest(
            url=request.url,
            summary_type="brief",
            language=request.language,
        )
        final = await self._summary.summarize_from_url(summarize_body, trace_id=trace_id)

        learning_body = TranscriptLearningRequest(url=request.url, language=request.language)
        notes, quiz, flashcards = await asyncio.gather(
            self._learning.notes(learning_body),
            self._learning.quiz(learning_body),
            self._learning.flashcards(learning_body),
        )

        markdown = build_notes_export_markdown(final, notes, quiz, flashcards)
        filename = suggest_export_filename(final.video_id, final.title)
        return ExportNotesResponse(markdown_content=markdown, suggested_filename=filename)


def build_default_export_notes_service(settings: Settings) -> ExportNotesService:
    return ExportNotesService(
        summary=build_default_summary_service(settings),
        learning=build_default_learning_service(settings),
    )

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.exceptions import (
    InvalidYouTubeUrlError,
    LLMConfigurationError,
    LLMInvocationError,
    TranscriptFetchError,
    UnsupportedLLMProviderError,
)
from app.models.request_models import ExportNotesRequest, TranscriptLearningRequest
from app.models.response_models import (
    ExportNotesResponse,
    FlashcardsResponse,
    InterviewPrepResponse,
    NotesResponse,
    QuizResponse,
)
from app.routers.error_mapping import transcript_fetch_status_code
from app.services.export_notes_service import ExportNotesService, build_default_export_notes_service
from app.services.learning_service import LearningService, build_default_learning_service

router = APIRouter()


def get_learning_service() -> LearningService:
    return build_default_learning_service(settings)


def get_export_notes_service() -> ExportNotesService:
    return build_default_export_notes_service(settings)


@router.post("/notes", response_model=NotesResponse)
async def generate_notes(
    body: TranscriptLearningRequest,
    service: Annotated[LearningService, Depends(get_learning_service)],
) -> NotesResponse:
    try:
        return await service.notes(body)
    except InvalidYouTubeUrlError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TranscriptFetchError as exc:
        raise HTTPException(transcript_fetch_status_code(str(exc)), detail=str(exc)) from exc
    except UnsupportedLLMProviderError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
    except LLMConfigurationError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMInvocationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/quiz", response_model=QuizResponse)
async def generate_quiz(
    body: TranscriptLearningRequest,
    service: Annotated[LearningService, Depends(get_learning_service)],
) -> QuizResponse:
    try:
        return await service.quiz(body)
    except InvalidYouTubeUrlError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TranscriptFetchError as exc:
        raise HTTPException(transcript_fetch_status_code(str(exc)), detail=str(exc)) from exc
    except UnsupportedLLMProviderError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
    except LLMConfigurationError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMInvocationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/flashcards", response_model=FlashcardsResponse)
async def generate_flashcards(
    body: TranscriptLearningRequest,
    service: Annotated[LearningService, Depends(get_learning_service)],
) -> FlashcardsResponse:
    try:
        return await service.flashcards(body)
    except InvalidYouTubeUrlError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TranscriptFetchError as exc:
        raise HTTPException(transcript_fetch_status_code(str(exc)), detail=str(exc)) from exc
    except UnsupportedLLMProviderError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
    except LLMConfigurationError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMInvocationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/interview-prep", response_model=InterviewPrepResponse)
async def generate_interview_prep(
    body: TranscriptLearningRequest,
    service: Annotated[LearningService, Depends(get_learning_service)],
) -> InterviewPrepResponse:
    """Transcript-grounded developer interview prep: Q&A, system-design angles, and edge cases."""
    try:
        return await service.interview_prep(body)
    except InvalidYouTubeUrlError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TranscriptFetchError as exc:
        raise HTTPException(transcript_fetch_status_code(str(exc)), detail=str(exc)) from exc
    except UnsupportedLLMProviderError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
    except LLMConfigurationError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMInvocationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/export-notes", response_model=ExportNotesResponse)
async def export_notes_markdown(
    body: ExportNotesRequest,
    service: Annotated[ExportNotesService, Depends(get_export_notes_service)],
) -> ExportNotesResponse:
    try:
        return await service.export_markdown(body)
    except InvalidYouTubeUrlError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TranscriptFetchError as exc:
        raise HTTPException(transcript_fetch_status_code(str(exc)), detail=str(exc)) from exc
    except UnsupportedLLMProviderError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
    except LLMConfigurationError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMInvocationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

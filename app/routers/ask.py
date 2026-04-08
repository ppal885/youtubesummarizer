from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.exceptions import (
    BackendWorkflowError,
    DatabaseConfigurationError,
    EmbeddingConfigurationError,
    EmbeddingInvocationError,
    InvalidYouTubeUrlError,
    LLMConfigurationError,
    LLMInvocationError,
    TranscriptFetchError,
    UnsupportedLLMProviderError,
    UnsupportedRetrieverError,
)
from app.models.ask_stream_events import AskStreamErrorEvent
from app.models.request_models import AskRequest
from app.models.response_models import AskResponse
from app.observability.request_tracing import request_trace_stage
from app.routers.error_mapping import transcript_fetch_status_code
from app.services.qa_service import QAService, build_default_qa_service
from app.services.qa_streaming import iter_ask_sse_events

router = APIRouter()


def get_qa_service() -> QAService:
    return build_default_qa_service(settings)


def _sse_error_line(message: str) -> str:
    return f"data: {AskStreamErrorEvent(message=message).model_dump_json()}\n\n"


_STREAM_SETUP_ERRORS = (
    BackendWorkflowError,
    InvalidYouTubeUrlError,
    TranscriptFetchError,
    UnsupportedLLMProviderError,
    UnsupportedRetrieverError,
    DatabaseConfigurationError,
    EmbeddingConfigurationError,
    EmbeddingInvocationError,
    LLMConfigurationError,
    LLMInvocationError,
)


def _client_wants_event_stream(accept: str | None) -> bool:
    """True when ``Accept`` lists ``text/event-stream`` (supports q-values and multiple types)."""
    if not accept or not accept.strip():
        return False
    for raw in accept.split(","):
        mime = raw.strip().split(";")[0].strip().lower()
        if mime == "text/event-stream":
            return True
    return False


def build_ask_sse_streaming_response(body: AskRequest, db: Session) -> StreamingResponse:
    """Shared SSE body for ``POST /ask`` (negotiated) and ``POST /ask/stream`` (explicit)."""

    async def event_gen():
        try:
            with request_trace_stage("ask.sse_stream"):
                async for line in iter_ask_sse_events(body, db, settings=settings):
                    yield line
        except _STREAM_SETUP_ERRORS as exc:
            yield _sse_error_line(str(exc))
        except SQLAlchemyError as exc:
            yield _sse_error_line(f"Could not persist or read transcript chunks: {exc}")

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/ask",
    response_model=None,
    responses={
        200: {
            "description": (
                "Default: `AskResponse` JSON. "
                "Send header `Accept: text/event-stream` for SSE: repeated `data:` JSON lines with "
                "`type: delta` (`text` fragments) then `type: done` (final grounded `answer`, `sources`, `confidence`)."
            ),
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/AskResponse"},
                },
                "text/event-stream": {
                    "schema": {"type": "string", "format": "binary"},
                },
            },
        },
    },
)
async def ask_transcript_question(
    body: AskRequest,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[QAService, Depends(get_qa_service)],
    accept: Annotated[str | None, Header()] = None,
) -> AskResponse | StreamingResponse:
    """
    Answer a question using the transcript (RAG).

    **Backward compatible:** omit ``Accept`` or use ``application/json`` to receive a single JSON object.

    **Streaming:** set ``Accept: text/event-stream`` to receive the same SSE contract as ``POST /ask/stream``.
    """
    if _client_wants_event_stream(accept):
        return build_ask_sse_streaming_response(body, db)

    try:
        with request_trace_stage("ask.sync_invoke"):
            return await service.ask(body, db)
    except InvalidYouTubeUrlError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TranscriptFetchError as exc:
        raise HTTPException(transcript_fetch_status_code(str(exc)), detail=str(exc)) from exc
    except UnsupportedLLMProviderError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
    except UnsupportedRetrieverError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
    except DatabaseConfigurationError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except EmbeddingConfigurationError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except EmbeddingInvocationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except LLMConfigurationError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMInvocationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except BackendWorkflowError as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not persist or read transcript chunks: {exc}",
        ) from exc


@router.post("/ask/stream")
def ask_transcript_question_stream(
    body: AskRequest,
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    """
    Explicit SSE endpoint (same stream as ``POST /ask`` with ``Accept: text/event-stream``).

    - ``{"type":"delta","text":"..."}`` — append raw model fragments (order preserved).
    - ``{"type":"done","answer","sources","confidence"}`` — final grounded answer (may differ from raw stream).
    - ``{"type":"error","message"}`` — failure (HTTP 200 stream; inspect last event).
    """
    return build_ask_sse_streaming_response(body, db)

import time
import uuid

from sqlalchemy.orm import Session

from app.config import Settings
from app.demo.catalog import demo_ask_response, is_demo_video_for_settings
from app.exceptions import BackendWorkflowError
from app.models.request_models import AskRequest
from app.models.response_models import AskResponse, PipelinePerformanceMs
from app.observability.ask_pipeline import log_ask_line
from app.observability.llm_request_usage import llm_request_usage_context
from app.observability.request_context import trace_context
from app.repositories.transcript_chunk_repository import TranscriptChunkRepository
from app.services.llm import LLMService, get_llm_service
from app.services.retrieval import ChunkRetriever, get_chunk_retriever
from app.services.youtube_service import extract_video_id
from app.workflows.ask_graph import AskGraphDeps, build_copilot_ask_graph
from app.workflows.ask_state import CopilotAskState


class QAService:
    """Orchestrates transcript Q&A via the LangGraph copilot workflow."""

    def __init__(
        self,
        settings: Settings,
        llm: LLMService,
        retriever: ChunkRetriever,
        *,
        transcript_repo: TranscriptChunkRepository | None = None,
    ) -> None:
        self._settings = settings
        self._llm = llm
        self._retriever = retriever
        self._transcript_repo = transcript_repo or TranscriptChunkRepository()
        self._copilot_graph = build_copilot_ask_graph()

    async def ask(self, request: AskRequest, db: Session) -> AskResponse:
        trace_id = str(uuid.uuid4())
        started = time.perf_counter()
        video_id = extract_video_id(str(request.url))

        with trace_context(trace_id), llm_request_usage_context(
            endpoint="ask",
            video_id=video_id,
        ):
            log_ask_line(
                "ask.pipeline.start",
                trace_id=trace_id,
                video_id=video_id,
                language=request.language,
                question_length=len(request.question.strip()),
            )

            if is_demo_video_for_settings(self._settings, video_id):
                response = demo_ask_response(request.question)
                total_ms = round((time.perf_counter() - started) * 1000, 2)
                demo_perf = PipelinePerformanceMs(
                    transcript_fetch_ms=0.0,
                    chunking_ms=0.0,
                    llm_ms=0.0,
                    total_ms=total_ms,
                )
                log_ask_line(
                    "ask.pipeline.complete",
                    trace_id=trace_id,
                    video_id=video_id,
                    confidence=response.confidence,
                    confidence_score=response.confidence_score,
                    sources_count=len(response.sources),
                    elapsed_ms=total_ms,
                    demo_mode=True,
                )
                log_ask_line(
                    "ask.pipeline.metrics",
                    trace_id=trace_id,
                    video_id=video_id,
                    transcript_fetch_ms=demo_perf.transcript_fetch_ms,
                    chunking_ms=demo_perf.chunking_ms,
                    llm_ms=demo_perf.llm_ms,
                    total_ms=demo_perf.total_ms,
                    demo_mode=True,
                )
                return response.model_copy(update={"performance": demo_perf})

            deps = AskGraphDeps(
                settings=self._settings,
                llm=self._llm,
                retriever=self._retriever,
                transcript_repo=self._transcript_repo,
                db=db,
            )
            initial = CopilotAskState(
                url=str(request.url),
                question=request.question,
                language=request.language,
            )

            try:
                final = await self._copilot_graph.ainvoke(
                    initial,
                    config={"configurable": {"deps": deps}},
                )
                state = CopilotAskState.model_validate(final)
            except Exception as exc:
                log_ask_line(
                    "ask.pipeline.failed",
                    trace_id=trace_id,
                    video_id=video_id,
                    error_type=type(exc).__name__,
                    detail=str(exc),
                    elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
                )
                raise

            if state.final_response is None:
                detail = "Copilot ask graph finished without final_response."
                log_ask_line(
                    "ask.pipeline.failed",
                    trace_id=trace_id,
                    video_id=video_id,
                    error_type=BackendWorkflowError.__name__,
                    detail=detail,
                    elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
                )
                raise BackendWorkflowError(detail)

            log_ask_line(
                "ask.pipeline.complete",
                trace_id=trace_id,
                video_id=video_id,
                confidence=state.final_response.confidence,
                confidence_score=state.final_response.confidence_score,
                sources_count=len(state.final_response.sources),
                elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return state.final_response


def build_default_qa_service(settings: Settings) -> QAService:
    return QAService(
        settings=settings,
        llm=get_llm_service(settings),
        retriever=get_chunk_retriever(settings),
    )

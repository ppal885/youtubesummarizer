"""SSE streaming for transcript Q&A (retrieval first, answer tokens streamed, verify at end)."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator

from langchain_core.runnables import RunnableConfig
from sqlalchemy.orm import Session

from app.config import Settings
from app.copilot.answer_composer import AnswerComposerAgent
from app.copilot.verifier_agent import VerifierAgent
from app.demo.catalog import demo_ask_response, is_demo_video_for_settings, stream_demo_answer_chunks
from app.exceptions import BackendWorkflowError
from app.models.ask_stream_events import AskStreamDeltaEvent, AskStreamDoneEvent, AskStreamErrorEvent
from app.models.request_models import AskRequest
from app.models.response_models import AskResponse
from app.observability.ask_pipeline import log_ask_line
from app.observability.llm_request_usage import llm_request_usage_context
from app.observability.request_context import trace_context
from app.repositories.transcript_chunk_repository import TranscriptChunkRepository
from app.services.llm import get_llm_service
from app.services.multi_hop_qa import assess_multi_hop, build_answer_context_for_multi_hop
from app.services.retrieval import get_chunk_retriever
from app.services.youtube_service import extract_video_id
from app.utils.output_normalizer import normalize_ask_response
from app.workflows.ask_graph import AskGraphDeps, _hit_to_citation_source
from app.workflows.ask_retrieval_phase import run_copilot_until_composer_ready
from app.workflows.ask_state import CopilotAskState


def _sse_data(payload: AskStreamDeltaEvent | AskStreamDoneEvent | AskStreamErrorEvent) -> str:
    return f"data: {payload.model_dump_json()}\n\n"


_verifier = VerifierAgent()


async def iter_ask_sse_events(
    request: AskRequest,
    db: Session,
    *,
    settings: Settings,
) -> AsyncIterator[str]:
    """
    Yield ``text/event-stream`` lines (``data: ...`` JSON).

    Deltas contain raw model text. The final ``done`` event carries verified ``answer``,
    ``sources``, and ``confidence`` and may differ from the streamed draft.
    """
    url_s = str(request.url).strip()
    question_s = request.question.strip()
    video_id = extract_video_id(url_s)
    trace_id = str(uuid.uuid4())
    started = time.perf_counter()

    with trace_context(trace_id), llm_request_usage_context(
        endpoint="ask_stream",
        video_id=video_id,
    ):
        log_ask_line(
            "ask.stream.start",
            trace_id=trace_id,
            video_id=video_id,
            language=request.language,
            question_length=len(question_s),
        )

        if is_demo_video_for_settings(settings, video_id):
            fr = normalize_ask_response(demo_ask_response(question_s))
            for fragment in stream_demo_answer_chunks(fr.answer):
                yield _sse_data(AskStreamDeltaEvent(text=fragment))
            yield _sse_data(
                AskStreamDoneEvent(
                    answer=fr.answer,
                    sources=list(fr.sources),
                    confidence=float(fr.confidence),
                    confidence_score=float(fr.confidence_score),
                )
            )
            log_ask_line(
                "ask.stream.complete",
                trace_id=trace_id,
                video_id=video_id,
                confidence=fr.confidence,
                confidence_score=fr.confidence_score,
                sources_count=len(fr.sources),
                elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
                demo_mode=True,
            )
            return

        deps = AskGraphDeps(
            settings=settings,
            llm=get_llm_service(settings),
            retriever=get_chunk_retriever(settings),
            transcript_repo=TranscriptChunkRepository(),
            db=db,
        )
        config: RunnableConfig = {"configurable": {"deps": deps}}
        initial = CopilotAskState(
            url=url_s,
            question=question_s,
            language=request.language,
        )

        try:
            state, phase = await run_copilot_until_composer_ready(initial, config)
        except Exception as exc:  # noqa: BLE001 - surfaced as SSE error
            log_ask_line(
                "ask.stream.failed",
                trace_id=trace_id,
                video_id=video_id,
                error_type=type(exc).__name__,
                detail=str(exc),
                elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            yield _sse_data(AskStreamErrorEvent(message=str(exc)))
            return

        if phase == "early_done":
            fr = state.final_response
            if fr is None:
                detail = "Ask pipeline ended without a response payload."
                err = BackendWorkflowError(detail)
                log_ask_line(
                    "ask.stream.failed",
                    trace_id=trace_id,
                    video_id=video_id,
                    error_type=type(err).__name__,
                    detail=detail,
                    elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
                )
                yield _sse_data(AskStreamErrorEvent(message=detail))
                return
            fr = normalize_ask_response(fr)
            yield _sse_data(
                AskStreamDoneEvent(
                    answer=fr.answer,
                    sources=list(fr.sources),
                    confidence=float(fr.confidence),
                    confidence_score=float(fr.confidence_score),
                )
            )
            log_ask_line(
                "ask.stream.complete",
                trace_id=trace_id,
                video_id=video_id,
                confidence=fr.confidence,
                confidence_score=fr.confidence_score,
                sources_count=len(fr.sources),
                elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
                early_done=True,
            )
            return

        composer = AnswerComposerAgent(deps.llm)
        multi_hop = assess_multi_hop(
            state.question,
            state.selected_passages,
            state.retrieved_chunks,
            query_intent=state.query_intent,
        )
        evidence = build_answer_context_for_multi_hop(
            multi_hop,
            state.selected_passages,
            state.retrieved_chunks,
        )
        raw_parts: list[str] = []
        try:
            async for fragment in composer.compose_stream(
                state.question,
                evidence,
                state.transcript_analysis,
                multi_hop=multi_hop,
            ):
                raw_parts.append(fragment)
                yield _sse_data(AskStreamDeltaEvent(text=fragment))
        except Exception as exc:  # noqa: BLE001
            log_ask_line(
                "ask.stream.failed",
                trace_id=trace_id,
                video_id=video_id,
                error_type=type(exc).__name__,
                detail=str(exc),
                elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            yield _sse_data(AskStreamErrorEvent(message=str(exc)))
            return

        raw = "".join(raw_parts).strip()
        vr = _verifier.verify(raw, evidence, multi_hop_assessment=multi_hop)
        final_response = normalize_ask_response(
            AskResponse(
                answer=vr.final_answer,
                sources=[_hit_to_citation_source(h) for h in state.citation_hits],
                confidence=float(vr.confidence),
                confidence_score=float(vr.confidence_score),
            )
        )

        yield _sse_data(
            AskStreamDoneEvent(
                answer=final_response.answer,
                sources=final_response.sources,
                confidence=float(final_response.confidence),
                confidence_score=float(final_response.confidence_score),
            )
        )
        log_ask_line(
            "ask.stream.complete",
            trace_id=trace_id,
            video_id=video_id,
            confidence=final_response.confidence,
            confidence_score=final_response.confidence_score,
            sources_count=len(final_response.sources),
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )

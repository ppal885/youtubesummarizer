"""Run summarization + copilot Q&A with timing and structured metrics."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Sequence

from sqlalchemy.orm import Session

from app.config import Settings
from app.evaluation.metrics import (
    chunk_coverage_score,
    lexical_support_ratio,
    retrieval_relevance_score,
)
from app.evaluation.models import (
    EvaluationAggregateMetrics,
    QuestionEvaluationResult,
    SummaryEvaluationResult,
    VideoEvaluationRun,
)
from app.models.request_models import SummarizeRequest
from app.repositories.transcript_chunk_repository import TranscriptChunkRepository
from app.services.chunk_service import chunk_transcript_items
from app.services.llm import get_llm_service
from app.services.retrieval import get_chunk_retriever
from app.services.summary_service import build_default_summary_service
from app.services.transcript_service import fetch_transcript_items, merge_transcript_text
from app.services.youtube_service import extract_video_id
from app.workflows.ask_graph import AskGraphDeps, build_copilot_ask_graph
from app.workflows.ask_state import CopilotAskState


def _preview(text: str, max_len: int = 400) -> str:
    t = text.strip().replace("\n", " ")
    if len(t) <= max_len:
        return t
    return f"{t[: max_len - 1]}…"


class CopilotEvaluationRunner:
    """
    Portfolio-friendly evaluator: reuses ``SummaryService`` and the compiled ask graph.

    Metrics are heuristic (lexical overlap, built-in verifier confidence)—no gold labels required.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._summary = build_default_summary_service(settings)
        self._llm = get_llm_service(settings)
        self._retriever = get_chunk_retriever(settings)
        self._repo = TranscriptChunkRepository()
        self._graph = build_copilot_ask_graph()

    def run(
        self,
        *,
        video_url: str,
        questions: Sequence[str],
        language: str,
        db: Session,
    ) -> VideoEvaluationRun:
        return asyncio.run(
            self._run_async(
                video_url=video_url,
                questions=questions,
                language=language,
                db=db,
            )
        )

    async def _run_async(
        self,
        *,
        video_url: str,
        questions: Sequence[str],
        language: str,
        db: Session,
    ) -> VideoEvaluationRun:
        url = video_url.strip()
        video_id = extract_video_id(url)
        if video_id is None:
            raise ValueError("Could not parse a valid YouTube video id from the URL.")

        items = fetch_transcript_items(video_id, language)
        merged = merge_transcript_text(items)
        transcript_len = len(merged)
        text_chunks = chunk_transcript_items(items, self._settings)
        total_chunks = len(text_chunks)

        summarize_req = SummarizeRequest(
            url=url,
            summary_type="brief",
            language=language,
        )
        t_sum0 = time.perf_counter()
        final_summary = await self._summary.summarize_from_url(
            summarize_req,
            trace_id=str(uuid.uuid4()),
        )
        summary_ms = round((time.perf_counter() - t_sum0) * 1000, 2)

        summary_body = f"{final_summary.summary}\n" + "\n".join(final_summary.bullets)
        faithfulness = lexical_support_ratio(summary_body, merged)

        summary_result = SummaryEvaluationResult(
            latency_ms=summary_ms,
            summary_faithfulness_score=faithfulness,
            chunks_processed=final_summary.chunks_processed,
            transcript_length=final_summary.transcript_length,
        )

        deps = AskGraphDeps(
            settings=self._settings,
            llm=self._llm,
            retriever=self._retriever,
            transcript_repo=self._repo,
            db=db,
        )
        config = {"configurable": {"deps": deps}}

        q_results: list[QuestionEvaluationResult] = []
        q_latencies: list[float] = []
        grounding_scores: list[float] = []
        relevance_scores: list[float] = []
        coverage_scores: list[float] = []

        for raw_q in questions:
            q = raw_q.strip()
            if not q:
                continue
            t0 = time.perf_counter()
            initial = CopilotAskState(url=url, question=q, language=language)
            final = await self._graph.ainvoke(initial, config=config)
            state = CopilotAskState.model_validate(final)
            q_ms = round((time.perf_counter() - t0) * 1000, 2)
            q_latencies.append(q_ms)

            fr = state.final_response
            if fr is None:
                raise RuntimeError("Ask graph finished without final_response during evaluation.")

            hits = list(state.retrieved_chunks)
            retrieved_n = len(hits)
            sources = list(fr.sources)
            cite_n = len(sources)

            rel = retrieval_relevance_score(q, hits)
            cov = chunk_coverage_score(hits, total_chunks)

            relevance_scores.append(rel)
            coverage_scores.append(cov)
            grounding_scores.append(float(fr.confidence_score))

            q_results.append(
                QuestionEvaluationResult(
                    question=q,
                    latency_ms=q_ms,
                    retrieved_chunk_count=retrieved_n,
                    citation_source_count=cite_n,
                    answer_has_sources=cite_n > 0,
                    answer_grounding_score=float(fr.confidence_score),
                    retrieval_relevance_score=rel,
                    chunk_coverage_score=cov,
                    answer_excerpt=_preview(fr.answer),
                )
            )

        n_q = len(q_results)
        all_latencies = [summary_ms, *q_latencies]
        avg_lat = round(sum(all_latencies) / max(1, len(all_latencies)), 2)

        mean_ground = round(sum(grounding_scores) / n_q, 4) if n_q else None
        mean_rel = round(sum(relevance_scores) / n_q, 4) if n_q else None
        mean_cov = round(sum(coverage_scores) / n_q, 4) if n_q else None

        aggregate = EvaluationAggregateMetrics(
            average_latency_ms=avg_lat,
            mean_answer_grounding_score=mean_ground,
            mean_retrieval_relevance=mean_rel,
            mean_chunk_coverage=mean_cov,
            summary_faithfulness_score=faithfulness,
        )

        return VideoEvaluationRun(
            video_url=url,
            video_id=video_id,
            language=language,
            transcript_char_count=transcript_len,
            total_transcript_chunks=total_chunks,
            summary=summary_result,
            questions=q_results,
            aggregate=aggregate,
        )


def run_video_evaluation(
    settings: Settings,
    *,
    video_url: str,
    questions: Sequence[str],
    language: str = "en",
    db: Session | None = None,
) -> VideoEvaluationRun:
    """
    Convenience: open a DB session when none is passed (matches API behavior for chunk persistence).
    """
    if db is not None:
        return CopilotEvaluationRunner(settings).run(
            video_url=video_url,
            questions=questions,
            language=language,
            db=db,
        )

    from app.db.session import SessionLocal

    session = SessionLocal()
    try:
        return CopilotEvaluationRunner(settings).run(
            video_url=video_url,
            questions=questions,
            language=language,
            db=session,
        )
    finally:
        session.close()

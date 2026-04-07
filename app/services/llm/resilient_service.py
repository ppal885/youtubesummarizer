from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import AsyncIterator, Callable
from typing import Any

from app.observability.llm_calls import log_llm_fallback, log_llm_retry, log_llm_safe_default
from app.services.llm.base import LLMService
from app.services.llm.schemas import QuizPayload

logger = logging.getLogger(__name__)


def _prov_label(svc: LLMService) -> tuple[str, str]:
    provider = getattr(svc, "_provider_name", None) or svc.__class__.__name__
    model = getattr(svc, "_model", None) or "unknown"
    return str(provider), str(model)


class ResilientLLMService(LLMService):
    """Wrap one or more LLM providers with simple failover and retry/backoff."""

    def __init__(
        self,
        *providers: LLMService,
        max_retries: int = 2,
        base_delay_seconds: float = 0.25,
        max_delay_seconds: float = 8.0,
        jitter_seconds: float = 0.25,
    ) -> None:
        if not providers:
            raise ValueError("ResilientLLMService requires at least one provider")
        self._providers = list(providers)
        self._max_retries = max(0, int(max_retries))
        self._base_delay = float(base_delay_seconds)
        self._max_delay = float(max_delay_seconds)
        self._jitter = float(jitter_seconds)

    async def _call_with_resilience_async(
        self,
        op_name: str,
        invoke: Callable[[LLMService], Any],
    ) -> Any:
        last_exc: Exception | None = None
        for ti, target in enumerate(self._providers):
            for attempt in range(self._max_retries + 1):
                try:
                    result = invoke(target)
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    if attempt >= self._max_retries:
                        logger.warning(
                            "LLM op %s failed for provider %s after %d attempts: %s",
                            op_name,
                            target.__class__.__name__,
                            attempt + 1,
                            exc,
                        )
                        if ti + 1 < len(self._providers):
                            nxt = self._providers[ti + 1]
                            fp, fm = _prov_label(target)
                            tp, tm = _prov_label(nxt)
                            log_llm_fallback(
                                capability=op_name,
                                from_provider=fp,
                                from_model=fm,
                                to_provider=tp,
                                to_model=tm,
                                detail=str(exc),
                            )
                        break
                    delay = min(self._max_delay, self._base_delay * (2**attempt))
                    delay += random.uniform(0, self._jitter)
                    p, m = _prov_label(target)
                    log_llm_retry(
                        provider=p,
                        model=m,
                        capability=op_name,
                        retry_number=attempt + 1,
                        delay_ms=delay * 1000,
                        detail=str(exc),
                        error_type=type(exc).__name__,
                    )
                    await asyncio.sleep(delay)
        assert last_exc is not None
        raise last_exc

    async def _stream_with_resilience_async(
        self,
        op_name: str,
        stream_factory: Callable[[LLMService], AsyncIterator[str]],
    ) -> AsyncIterator[str]:
        last_exc: Exception | None = None
        for ti, target in enumerate(self._providers):
            for attempt in range(self._max_retries + 1):
                try:
                    async for chunk in stream_factory(target):
                        yield chunk
                    return
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    if attempt >= self._max_retries:
                        logger.warning(
                            "LLM stream %s failed for provider %s after %d attempts: %s",
                            op_name,
                            target.__class__.__name__,
                            attempt + 1,
                            exc,
                        )
                        if ti + 1 < len(self._providers):
                            nxt = self._providers[ti + 1]
                            fp, fm = _prov_label(target)
                            tp, tm = _prov_label(nxt)
                            log_llm_fallback(
                                capability=op_name,
                                from_provider=fp,
                                from_model=fm,
                                to_provider=tp,
                                to_model=tm,
                                detail=str(exc),
                            )
                        break
                    delay = min(self._max_delay, self._base_delay * (2**attempt))
                    delay += random.uniform(0, self._jitter)
                    p, m = _prov_label(target)
                    log_llm_retry(
                        provider=p,
                        model=m,
                        capability=op_name,
                        retry_number=attempt + 1,
                        delay_ms=delay * 1000,
                        detail=str(exc),
                        error_type=type(exc).__name__,
                    )
                    await asyncio.sleep(delay)
        assert last_exc is not None
        raise last_exc

    async def summarize_chunk(
        self,
        chunk: str,
        summary_type: str,
        *,
        learning_level: str = "intermediate",
    ):
        return await self._call_with_resilience_async(
            "summarize_chunk",
            lambda svc: svc.summarize_chunk(
                chunk,
                summary_type,
                learning_level=learning_level,
            ),
        )

    async def merge_summaries(
        self,
        chunk_summaries,
        summary_type: str,
        *,
        learning_level: str = "intermediate",
    ):
        return await self._call_with_resilience_async(
            "merge_summaries",
            lambda svc: svc.merge_summaries(
                chunk_summaries,
                summary_type,
                learning_level=learning_level,
            ),
        )

    async def answer_question(
        self,
        question: str,
        context_passages,
        *,
        orientation_notes: str | None = None,
        evidence_synthesis_notes: str | None = None,
    ):
        return await self._call_with_resilience_async(
            "answer_question",
            lambda svc: svc.answer_question(
                question,
                context_passages,
                orientation_notes=orientation_notes,
                evidence_synthesis_notes=evidence_synthesis_notes,
            ),
        )

    async def answer_question_stream(
        self,
        question: str,
        context_passages,
        *,
        orientation_notes: str | None = None,
        evidence_synthesis_notes: str | None = None,
    ) -> AsyncIterator[str]:
        async for chunk in self._stream_with_resilience_async(
            "answer_question_stream",
            lambda svc: svc.answer_question_stream(
                question,
                context_passages,
                orientation_notes=orientation_notes,
                evidence_synthesis_notes=evidence_synthesis_notes,
            ),
        ):
            yield chunk

    async def compress_qa_retrieval_context(self, question: str, hits, target_count: int):
        return await self._call_with_resilience_async(
            "compress_qa_retrieval_context",
            lambda svc: svc.compress_qa_retrieval_context(question, hits, target_count),
        )

    async def generate_suggested_questions(self, transcript: str):
        return await self._call_with_resilience_async(
            "generate_suggested_questions",
            lambda svc: svc.generate_suggested_questions(transcript),
        )

    async def generate_chapters(self, segments):
        return await self._call_with_resilience_async(
            "generate_chapters",
            lambda svc: svc.generate_chapters(segments),
        )

    async def compare_two_video_summaries(
        self,
        *,
        title_1: str,
        summary_1: str,
        bullets_1: list[str],
        title_2: str,
        summary_2: str,
        bullets_2: list[str],
    ):
        return await self._call_with_resilience_async(
            "compare_two_video_summaries",
            lambda svc: svc.compare_two_video_summaries(
                title_1=title_1,
                summary_1=summary_1,
                bullets_1=bullets_1,
                title_2=title_2,
                summary_2=summary_2,
                bullets_2=bullets_2,
            ),
        )

    async def synthesize_multi_video_summaries(self, user_message: str):
        return await self._call_with_resilience_async(
            "synthesize_multi_video_summaries",
            lambda svc: svc.synthesize_multi_video_summaries(user_message),
        )

    async def generate_study_notes(self, user_message: str):
        return await self._call_with_resilience_async(
            "generate_study_notes",
            lambda svc: svc.generate_study_notes(user_message),
        )

    async def generate_quiz(self, user_message: str):
        try:
            return await self._call_with_resilience_async(
                "generate_quiz",
                lambda svc: svc.generate_quiz(user_message),
            )
        except Exception as exc:  # noqa: BLE001
            p, m = _prov_label(self._providers[-1])
            log_llm_safe_default(
                provider=p,
                model=m,
                capability="generate_quiz",
                detail=str(exc),
                error_type=type(exc).__name__,
            )
            return QuizPayload(questions=[])

    async def generate_flashcards(self, user_message: str):
        return await self._call_with_resilience_async(
            "generate_flashcards",
            lambda svc: svc.generate_flashcards(user_message),
        )

    async def generate_interview_prep(self, user_message: str):
        return await self._call_with_resilience_async(
            "generate_interview_prep",
            lambda svc: svc.generate_interview_prep(user_message),
        )

    async def generate_developer_study_digest(self, user_message: str):
        return await self._call_with_resilience_async(
            "generate_developer_study_digest",
            lambda svc: svc.generate_developer_study_digest(user_message),
        )

    async def understand_qa_query(self, question: str):
        return await self._call_with_resilience_async(
            "understand_qa_query",
            lambda svc: svc.understand_qa_query(question),
        )

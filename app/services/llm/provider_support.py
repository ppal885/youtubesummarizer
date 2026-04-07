"""Shared helpers for provider implementations."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.observability.llm_request_usage import record_llm_usage
from app.exceptions import LLMInvocationError
from app.models.response_models import DeveloperStudyDigest, QAResponse
from app.observability.llm_calls import (
    aiter_logged_call,
    iter_logged_call,
    log_llm_cache_event,
    log_llm_invalid_output,
    log_llm_retry,
    run_logged_call,
    run_logged_call_async,
)
from app.services.llm.json_parse import parse_llm_json_object
from app.services.llm.prompt_cache import get_prompt_response_cache
from app.services.llm.schemas import (
    ChaptersLlmPayload,
    CompressedQaContextPayload,
    FlashcardsPayload,
    LearningNotesPayload,
    MultiVideoSynthesisPayload,
    QaQueryUnderstandingPayload,
    QuizPayload,
    StructuredSummaryPayload,
    SuggestedQuestionsPayload,
    VideoPairComparePayload,
    InterviewPrepPayload,
)
from app.services.llm.token_usage import TokenUsageMetrics, build_token_usage_metrics

T = TypeVar("T")
PayloadT = TypeVar("PayloadT", bound=BaseModel)

_MAX_STRUCTURED_OUTPUT_ATTEMPTS = 3
_STRUCTURED_RETRY_BASE_DELAY_SECONDS = 0.25
_PROMPT_CACHE_TTL_SECONDS = 300.0


def _json_schema_text(payload_model: type[PayloadT]) -> str:
    schema = payload_model.model_json_schema()
    return json.dumps(schema, ensure_ascii=False, sort_keys=True)


def _strict_structured_system_prompt(
    system_prompt: str,
    payload_model: type[PayloadT],
) -> str:
    return (
        f"{system_prompt.strip()}\n\n"
        "STRICT OUTPUT CONTRACT:\n"
        "- Return exactly one valid JSON object.\n"
        "- Do not include markdown fences.\n"
        "- Do not include any explanation, preamble, or trailing text.\n"
        "- The JSON must match this schema exactly.\n"
        "- Use empty strings or empty arrays when the content is unavailable.\n"
        f"JSON_SCHEMA:\n{_json_schema_text(payload_model)}"
    )


def _structured_retry_user_message(
    user_message: str,
    *,
    attempt: int,
    last_error: str | None,
) -> str:
    if attempt <= 1 or not last_error:
        return user_message
    return (
        f"{user_message.rstrip()}\n\n"
        "RETRY INSTRUCTION:\n"
        "Your previous response was not valid for the required JSON contract.\n"
        f"Validation issue: {last_error}\n"
        "Return ONLY the corrected JSON object and nothing else."
    )


def safe_structured_default(payload_model: type[PayloadT]) -> PayloadT:
    defaults: dict[type[BaseModel], dict[str, Any]] = {
        StructuredSummaryPayload: {"summary": "", "bullets": []},
        QAResponse: {"answer": "Not mentioned in video"},
        SuggestedQuestionsPayload: {"questions": []},
        VideoPairComparePayload: {"similarities": [], "differences": []},
        MultiVideoSynthesisPayload: {
            "combined_summary": "",
            "common_ideas": [],
            "differences": [],
            "best_explanation": "",
        },
        LearningNotesPayload: {
            "concise_notes": "",
            "detailed_notes": "",
            "glossary_terms": [],
        },
        QuizPayload: {"questions": []},
        FlashcardsPayload: {"cards": []},
        InterviewPrepPayload: {
            "key_questions": [],
            "system_design_insights": [],
            "edge_cases": [],
        },
        ChaptersLlmPayload: {"chapters": []},
        CompressedQaContextPayload: {"items": []},
        QaQueryUnderstandingPayload: {
            "intent": "factual",
            "normalized_query": "",
            "expansion_keywords": [],
        },
        DeveloperStudyDigest: {},
    }

    for model_type, default_data in defaults.items():
        if issubclass(payload_model, model_type):
            try:
                return payload_model.model_validate(default_data)
            except ValidationError:
                return payload_model.model_construct(**default_data)

    try:
        return payload_model()
    except ValidationError as exc:
        raise LLMInvocationError(
            f"No safe structured fallback is available for {payload_model.__name__}: {exc}"
        ) from exc


def _is_retryable_structured_error(exc: Exception) -> bool:
    message = str(exc)
    return "returned no content" in message or "invalid structured output" in message


class LoggedLLMProviderMixin:
    _provider_name: str
    _model: str

    def _run_logged(self, capability: str, fn: Callable[[], T]) -> T:
        return run_logged_call(
            provider=self._provider_name,
            model=self._model,
            capability=capability,
            fn=fn,
        )

    def _iter_logged(self, capability: str, factory: Callable[[], Iterator[str]]) -> Iterator[str]:
        return iter_logged_call(
            provider=self._provider_name,
            model=self._model,
            capability=capability,
            factory=factory,
        )

    def _transport_error(self, capability: str, exc: Exception) -> LLMInvocationError:
        return LLMInvocationError(
            f"{self._provider_name} {capability} request failed: {exc}"
        )

    def _empty_content_error(self, capability: str) -> LLMInvocationError:
        return LLMInvocationError(
            f"{self._provider_name} {capability} returned no content."
        )

    def _build_prompt_cache_envelope(
        self,
        capability: str,
        prompt_kind: str,
        system_prompt: str,
        user_message: str,
    ) -> str:
        return (
            f"provider={self._provider_name}\n"
            f"model={self._model}\n"
            f"capability={capability}\n"
            f"prompt_kind={prompt_kind}\n"
            f"system:\n{system_prompt.strip()}\n"
            f"user:\n{user_message.strip()}"
        )

    def _lookup_prompt_cache(
        self,
        capability: str,
        prompt_kind: str,
        system_prompt: str,
        user_message: str,
    ) -> tuple[str | None, str, str]:
        prompt = self._build_prompt_cache_envelope(
            capability,
            prompt_kind,
            system_prompt,
            user_message,
        )
        cached_value, cache_key = get_prompt_response_cache().get(prompt)
        log_llm_cache_event(
            provider=self._provider_name,
            model=self._model,
            capability=capability,
            cache_key=cache_key,
            hit=cached_value is not None,
        )
        return cached_value, cache_key, prompt

    def _store_prompt_cache(self, prompt: str, value: str) -> None:
        get_prompt_response_cache().set(
            prompt,
            value,
            ttl_seconds=_PROMPT_CACHE_TTL_SECONDS,
        )

    def _delete_prompt_cache(self, prompt: str) -> None:
        get_prompt_response_cache().delete(prompt)

    def _record_usage(
        self,
        capability: str,
        *,
        input_text: str | None,
        output_text: str | None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
    ) -> TokenUsageMetrics:
        metrics = build_token_usage_metrics(
            provider=self._provider_name,
            model=self._model,
            input_text=input_text,
            output_text=output_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
        record_llm_usage(
            provider=self._provider_name,
            model=self._model,
            capability=capability,
            metrics=metrics,
        )
        return metrics

    def _parse_structured_payload(
        self,
        capability: str,
        content: str | None,
        payload_model: type[PayloadT],
    ) -> PayloadT:
        if not content or not content.strip():
            raise self._empty_content_error(capability)
        try:
            return parse_llm_json_object(content, payload_model)
        except ValueError as exc:
            raise LLMInvocationError(
                f"{self._provider_name} {capability} returned invalid structured output: {exc}"
            ) from exc

    def _structured_completion_with_retry(
        self,
        capability: str,
        system_prompt: str,
        user_message: str,
        payload_model: type[PayloadT],
        *,
        raw_completion: Callable[[str, str, str], str],
    ) -> PayloadT:
        strict_system_prompt = _strict_structured_system_prompt(system_prompt, payload_model)
        last_error: str | None = None
        last_output: str | None = None
        cached_output, _, cache_prompt = self._lookup_prompt_cache(
            capability,
            "structured",
            strict_system_prompt,
            user_message,
        )
        if cached_output is not None:
            try:
                return self._parse_structured_payload(capability, cached_output, payload_model)
            except LLMInvocationError:
                self._delete_prompt_cache(cache_prompt)

        for attempt in range(1, _MAX_STRUCTURED_OUTPUT_ATTEMPTS + 1):
            attempt_user_message = _structured_retry_user_message(
                user_message,
                attempt=attempt,
                last_error=last_error,
            )
            try:
                last_output = raw_completion(capability, strict_system_prompt, attempt_user_message)
                parsed = self._parse_structured_payload(capability, last_output, payload_model)
                self._store_prompt_cache(cache_prompt, last_output)
                return parsed
            except LLMInvocationError as exc:
                if not _is_retryable_structured_error(exc):
                    raise
                last_error = str(exc)
                log_llm_invalid_output(
                    provider=self._provider_name,
                    model=self._model,
                    capability=capability,
                    attempt=attempt,
                    detail=last_error,
                    raw_output=last_output,
                    fallback_used=attempt == _MAX_STRUCTURED_OUTPUT_ATTEMPTS,
                )
                if attempt < _MAX_STRUCTURED_OUTPUT_ATTEMPTS:
                    delay_seconds = _STRUCTURED_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                    log_llm_retry(
                        provider=self._provider_name,
                        model=self._model,
                        capability=capability,
                        retry_number=attempt,
                        delay_ms=delay_seconds * 1000,
                        detail=last_error,
                        error_type=type(exc).__name__,
                    )
                    time.sleep(delay_seconds)

        return safe_structured_default(payload_model)

    async def _run_logged_async(self, capability: str, fn: Callable[[], Awaitable[T]]) -> T:
        return await run_logged_call_async(
            provider=self._provider_name,
            model=self._model,
            capability=capability,
            fn=fn,
        )

    async def _iter_logged_async(
        self, capability: str, factory: Callable[[], AsyncIterator[str]]
    ) -> AsyncIterator[str]:
        async for chunk in aiter_logged_call(
            provider=self._provider_name,
            model=self._model,
            capability=capability,
            factory=factory,
        ):
            yield chunk

    async def _structured_completion_with_retry_async(
        self,
        capability: str,
        system_prompt: str,
        user_message: str,
        payload_model: type[PayloadT],
        *,
        raw_completion: Callable[[str, str, str], Awaitable[str]],
    ) -> PayloadT:
        strict_system_prompt = _strict_structured_system_prompt(system_prompt, payload_model)
        last_error: str | None = None
        last_output: str | None = None
        cached_output, _, cache_prompt = self._lookup_prompt_cache(
            capability,
            "structured_async",
            strict_system_prompt,
            user_message,
        )
        if cached_output is not None:
            try:
                return self._parse_structured_payload(capability, cached_output, payload_model)
            except LLMInvocationError:
                self._delete_prompt_cache(cache_prompt)

        for attempt in range(1, _MAX_STRUCTURED_OUTPUT_ATTEMPTS + 1):
            attempt_user_message = _structured_retry_user_message(
                user_message,
                attempt=attempt,
                last_error=last_error,
            )
            try:
                last_output = await raw_completion(capability, strict_system_prompt, attempt_user_message)
                parsed = self._parse_structured_payload(capability, last_output, payload_model)
                self._store_prompt_cache(cache_prompt, last_output)
                return parsed
            except LLMInvocationError as exc:
                if not _is_retryable_structured_error(exc):
                    raise
                last_error = str(exc)
                log_llm_invalid_output(
                    provider=self._provider_name,
                    model=self._model,
                    capability=capability,
                    attempt=attempt,
                    detail=last_error,
                    raw_output=last_output,
                    fallback_used=attempt == _MAX_STRUCTURED_OUTPUT_ATTEMPTS,
                )
                if attempt < _MAX_STRUCTURED_OUTPUT_ATTEMPTS:
                    delay_seconds = _STRUCTURED_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                    log_llm_retry(
                        provider=self._provider_name,
                        model=self._model,
                        capability=capability,
                        retry_number=attempt,
                        delay_ms=delay_seconds * 1000,
                        detail=last_error,
                        error_type=type(exc).__name__,
                    )
                    await asyncio.sleep(delay_seconds)

        return safe_structured_default(payload_model)

    def _stream_with_prompt_cache(
        self,
        capability: str,
        system_prompt: str,
        user_message: str,
        factory: Callable[[], Iterator[str]],
    ) -> Iterator[str]:
        cached_output, _, cache_prompt = self._lookup_prompt_cache(
            capability,
            "stream",
            system_prompt,
            user_message,
        )
        if cached_output is not None:
            def _cached() -> Iterator[str]:
                if cached_output:
                    yield cached_output

            return _cached()

        def _caching_factory() -> Iterator[str]:
            parts: list[str] = []
            for chunk in factory():
                parts.append(chunk)
                yield chunk
            if parts:
                self._store_prompt_cache(cache_prompt, "".join(parts))

        return self._iter_logged(capability, _caching_factory)

    async def _stream_with_prompt_cache_async(
        self,
        capability: str,
        system_prompt: str,
        user_message: str,
        factory: Callable[[], AsyncIterator[str]],
    ) -> AsyncIterator[str]:
        cached_output, _, cache_prompt = self._lookup_prompt_cache(
            capability,
            "stream",
            system_prompt,
            user_message,
        )
        if cached_output is not None:

            async def _cached() -> AsyncIterator[str]:
                if cached_output:
                    yield cached_output

            async for line in _cached():
                yield line
            return

        async def _caching_factory() -> AsyncIterator[str]:
            parts: list[str] = []
            async for chunk in factory():
                parts.append(chunk)
                yield chunk
            if parts:
                self._store_prompt_cache(cache_prompt, "".join(parts))

        async for chunk in self._iter_logged_async(capability, _caching_factory):
            yield chunk

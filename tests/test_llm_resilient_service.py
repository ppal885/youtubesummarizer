from collections.abc import AsyncIterator

import pytest

from app.config import Settings
from app.exceptions import LLMInvocationError
from app.models.qa_models import TranscriptChunkPassage
from app.models.summary_models import ChunkSummary
from app.services.llm.factory import get_llm_service
from app.services.llm.mock_provider import MockLLMService
from app.services.llm.resilient_service import ResilientLLMService
from app.services.llm.schemas import QuizPayload


class _FlakySummaryService(MockLLMService):
    _provider_name = "flaky"
    _model = "gpt-main"

    def __init__(self, failures_before_success: int) -> None:
        super().__init__()
        self.calls = 0
        self.failures_before_success = failures_before_success

    async def summarize_chunk(
        self,
        chunk: str,
        summary_type: str,
        *,
        learning_level: str = "intermediate",
    ) -> ChunkSummary:
        self.calls += 1
        if self.calls <= self.failures_before_success:
            raise LLMInvocationError("Rate limit exceeded on upstream LLM.")
        return ChunkSummary(summary=f"{summary_type}:{chunk}", bullets=[learning_level])


class _FailingQuizService(MockLLMService):
    _provider_name = "broken"
    _model = "broken-model"

    async def generate_quiz(self, user_message: str) -> QuizPayload:
        raise LLMInvocationError("Service unavailable while generating quiz.")


class _FailingStreamService(MockLLMService):
    _provider_name = "streamy"
    _model = "stream-main"

    async def answer_question_stream(
        self,
        question: str,
        context_passages: list[TranscriptChunkPassage],
        *,
        orientation_notes: str | None = None,
        evidence_synthesis_notes: str | None = None,
    ) -> AsyncIterator[str]:
        raise LLMInvocationError("Request timed out while streaming.")
        yield ""  # pragma: no cover — keeps this an async generator for the type checker


class _SuccessfulStreamService(MockLLMService):
    _provider_name = "streamy"
    _model = "stream-fallback"

    async def answer_question_stream(
        self,
        question: str,
        context_passages: list[TranscriptChunkPassage],
        *,
        orientation_notes: str | None = None,
        evidence_synthesis_notes: str | None = None,
    ) -> AsyncIterator[str]:
        yield "Recovered "
        yield "stream"


class _FactoryOpenAIStub(MockLLMService):
    _provider_name = "openai-compatible"

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._model = settings.llm_model

    async def summarize_chunk(
        self,
        chunk: str,
        summary_type: str,
        *,
        learning_level: str = "intermediate",
    ) -> ChunkSummary:
        if self._model == "gpt-4o":
            raise LLMInvocationError("Primary model unavailable.")
        return ChunkSummary(summary=f"fallback:{self._model}", bullets=[summary_type, learning_level])


def _sample_passages() -> list[TranscriptChunkPassage]:
    return [
        TranscriptChunkPassage(
            id=1,
            chunk_index=0,
            start_seconds=12.0,
            text="Redis is used as a cache in this segment.",
        )
    ]


@pytest.mark.asyncio
async def test_resilient_service_retries_with_exponential_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_calls: list[float] = []
    retry_logs: list[dict] = []

    async def _fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    service = ResilientLLMService(_FlakySummaryService(failures_before_success=2))
    monkeypatch.setattr(
        "app.services.llm.resilient_service.asyncio.sleep",
        _fake_sleep,
    )
    monkeypatch.setattr("app.services.llm.resilient_service.random.uniform", lambda _a, _b: 0.0)
    monkeypatch.setattr(
        "app.services.llm.resilient_service.log_llm_retry",
        lambda **kwargs: retry_logs.append(kwargs),
    )

    payload = await service.summarize_chunk("chunk text", "bullet")

    assert payload.summary == "bullet:chunk text"
    assert sleep_calls == [0.25, 0.5]
    assert [log["retry_number"] for log in retry_logs] == [1, 2]


@pytest.mark.asyncio
async def test_resilient_service_uses_safe_default_when_all_targets_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    safe_default_logs: list[dict] = []
    primary = _FailingQuizService()
    fallback = _FailingQuizService()
    fallback._model = "smaller-model"
    service = ResilientLLMService(primary, fallback)

    async def _noop_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(
        "app.services.llm.resilient_service.asyncio.sleep",
        _noop_sleep,
    )
    monkeypatch.setattr(
        "app.services.llm.resilient_service.log_llm_safe_default",
        lambda **kwargs: safe_default_logs.append(kwargs),
    )
    monkeypatch.setattr(
        "app.services.llm.resilient_service.log_llm_fallback",
        lambda **kwargs: None,
    )

    payload = await service.generate_quiz("prompt")

    assert payload.questions == []
    assert len(safe_default_logs) == 1


@pytest.mark.asyncio
async def test_resilient_service_streams_from_fallback_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_calls: list[float] = []
    fallback_logs: list[dict] = []

    async def _fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    service = ResilientLLMService(_FailingStreamService(), _SuccessfulStreamService())
    monkeypatch.setattr(
        "app.services.llm.resilient_service.asyncio.sleep",
        _fake_sleep,
    )
    monkeypatch.setattr("app.services.llm.resilient_service.random.uniform", lambda _a, _b: 0.0)
    monkeypatch.setattr(
        "app.services.llm.resilient_service.log_llm_fallback",
        lambda **kwargs: fallback_logs.append(kwargs),
    )

    chunks: list[str] = []
    async for frag in service.answer_question_stream("What is Redis?", _sample_passages()):
        chunks.append(frag)

    assert "".join(chunks) == "Recovered stream"
    assert sleep_calls == [0.25, 0.5]
    assert len(fallback_logs) == 1


@pytest.mark.asyncio
async def test_factory_adds_smaller_model_fallback_before_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.llm.factory.OpenAICompatibleLLMService",
        _FactoryOpenAIStub,
    )

    service = get_llm_service(
        Settings(
            llm_provider="openai",
            llm_api_key="k",
            llm_model="gpt-4o",
        )
    )

    assert isinstance(service, ResilientLLMService)
    payload = await service.summarize_chunk("chunk text", "brief")
    assert payload.summary == "fallback:gpt-4o-mini"

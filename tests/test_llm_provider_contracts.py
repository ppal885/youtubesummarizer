from types import SimpleNamespace

import pytest
from anthropic import AnthropicError
from openai import OpenAIError

from app.config import Settings
from app.exceptions import LLMInvocationError
from app.models.qa_models import TranscriptChunkPassage
from app.models.response_models import QAResponse
from app.models.retrieval_models import RetrievalHit
from app.services.llm.anthropic_provider import AnthropicLLMService
from app.services.llm.mock_provider import MockLLMService
from app.services.llm.openai_provider import OpenAICompatibleLLMService
from app.services.llm.prompt_cache import InMemoryPromptCache


class _AsyncListIter:
    def __init__(self, items: list[object]) -> None:
        self._items = items
        self._i = 0

    def __aiter__(self) -> "_AsyncListIter":
        return self

    async def __anext__(self) -> object:
        if self._i >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._i]
        self._i += 1
        return item


class _FakeOpenAIChatCompletions:
    def __init__(
        self,
        *,
        contents: list[str] | None = None,
        stream_chunks: list[str] | None = None,
        usages: list[object] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.contents = list(contents or [])
        self.stream_chunks = list(stream_chunks or [])
        self.usages = list(usages or [])
        self.error = error
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        if kwargs.get("stream"):
            chunks = [
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content=chunk))]
                )
                for chunk in self.stream_chunks
            ]
            return _AsyncListIter(chunks)
        content = self.contents.pop(0) if self.contents else None
        usage = self.usages.pop(0) if self.usages else None
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=usage,
        )


class _FakeOpenAIClient:
    def __init__(self, completions: _FakeOpenAIChatCompletions) -> None:
        self.chat = SimpleNamespace(completions=completions)


class _FakeAnthropicMessages:
    def __init__(
        self,
        *,
        contents: list[str] | None = None,
        stream_chunks: list[str] | None = None,
        usages: list[object] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.contents = list(contents or [])
        self.stream_chunks = list(stream_chunks or [])
        self.usages = list(usages or [])
        self.error = error
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        content = self.contents.pop(0) if self.contents else ""
        usage = self.usages.pop(0) if self.usages else None
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=content)],
            usage=usage,
        )

    def stream(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return _FakeAnthropicAsyncStreamManager(self.stream_chunks)


class _AsyncTextStream:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = list(chunks)
        self._i = 0

    def __aiter__(self) -> "_AsyncTextStream":
        return self

    async def __anext__(self) -> str:
        if self._i >= len(self._chunks):
            raise StopAsyncIteration
        t = self._chunks[self._i]
        self._i += 1
        return t


class _FakeAnthropicAsyncStreamManager:
    def __init__(self, stream_chunks: list[str]) -> None:
        self._stream_chunks = stream_chunks

    async def __aenter__(self) -> SimpleNamespace:
        return SimpleNamespace(text_stream=_AsyncTextStream(self._stream_chunks))

    async def __aexit__(self, *args: object) -> bool:
        return False


class _FakeAnthropicClient:
    def __init__(self, messages: _FakeAnthropicMessages) -> None:
        self.messages = messages


@pytest.fixture(autouse=True)
def _isolated_prompt_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    cache = InMemoryPromptCache()
    monkeypatch.setattr(
        "app.services.llm.provider_support.get_prompt_response_cache",
        lambda: cache,
    )


def _sample_passages() -> list[TranscriptChunkPassage]:
    return [
        TranscriptChunkPassage(
            id=1,
            chunk_index=0,
            start_seconds=12.0,
            text="Redis is used as a cache in this segment.",
        )
    ]


def _sample_hits() -> list[RetrievalHit]:
    passage = _sample_passages()[0]
    return [
        RetrievalHit(
            passage=passage,
            semantic_score=0.8,
            keyword_score=0.7,
            final_score=0.75,
            ranking_explanation="unit-test",
        ),
        RetrievalHit(
            passage=TranscriptChunkPassage(
                id=2,
                chunk_index=1,
                start_seconds=18.0,
                text="A second chunk with adjacent evidence.",
            ),
            semantic_score=0.7,
            keyword_score=0.8,
            final_score=0.75,
            ranking_explanation="unit-test",
        ),
        RetrievalHit(
            passage=TranscriptChunkPassage(
                id=3,
                chunk_index=2,
                start_seconds=25.0,
                text="A third chunk to satisfy compression payload constraints.",
            ),
            semantic_score=0.6,
            keyword_score=0.8,
            final_score=0.72,
            ranking_explanation="unit-test",
        ),
    ]


@pytest.mark.asyncio
async def test_openai_structured_calls_use_json_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    completions = _FakeOpenAIChatCompletions(
        contents=['{"summary":"hello","bullets":["one"]}']
    )
    monkeypatch.setattr(
        "app.services.llm.openai_provider.AsyncOpenAI",
        lambda **kwargs: _FakeOpenAIClient(completions),
    )

    service = OpenAICompatibleLLMService(
        Settings(llm_provider="openai", llm_api_key="k", llm_model="gpt-test")
    )
    out = await service.summarize_chunk("chunk text", "brief")

    assert out.summary == "hello"
    assert out.bullets == ["one"]
    assert completions.calls[0]["response_format"] == {"type": "json_object"}
    assert "STRICT OUTPUT CONTRACT" in completions.calls[0]["messages"][0]["content"]
    assert "Do not include markdown fences" in completions.calls[0]["messages"][0]["content"]


@pytest.mark.asyncio
async def test_openai_structured_calls_retry_on_invalid_json_then_succeed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completions = _FakeOpenAIChatCompletions(
        contents=[
            "not json",
            '{"concise_notes":"short","detailed_notes":"long","glossary_terms":[]}',
        ]
    )
    invalid_logs: list[dict] = []
    retry_logs: list[dict] = []
    sleep_calls: list[float] = []
    monkeypatch.setattr(
        "app.services.llm.openai_provider.AsyncOpenAI",
        lambda **kwargs: _FakeOpenAIClient(completions),
    )
    monkeypatch.setattr(
        "app.services.llm.provider_support.log_llm_invalid_output",
        lambda **kwargs: invalid_logs.append(kwargs),
    )
    monkeypatch.setattr(
        "app.services.llm.provider_support.log_llm_retry",
        lambda **kwargs: retry_logs.append(kwargs),
    )

    async def _fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr(
        "app.services.llm.provider_support.asyncio.sleep",
        _fake_sleep,
    )
    service = OpenAICompatibleLLMService(
        Settings(llm_provider="openai", llm_api_key="k", llm_model="gpt-test")
    )

    payload = await service.generate_study_notes("prompt")
    assert payload.concise_notes == "short"
    assert payload.detailed_notes == "long"
    assert len(completions.calls) == 2
    assert len(invalid_logs) == 1
    assert invalid_logs[0]["attempt"] == 1
    assert len(retry_logs) == 1
    assert retry_logs[0]["retry_number"] == 1
    assert sleep_calls == [0.25]


@pytest.mark.asyncio
async def test_openai_stream_raises_on_empty_content(monkeypatch: pytest.MonkeyPatch) -> None:
    completions = _FakeOpenAIChatCompletions(stream_chunks=[])
    monkeypatch.setattr(
        "app.services.llm.openai_provider.AsyncOpenAI",
        lambda **kwargs: _FakeOpenAIClient(completions),
    )
    service = OpenAICompatibleLLMService(
        Settings(llm_provider="openai", llm_api_key="k", llm_model="gpt-test")
    )

    with pytest.raises(LLMInvocationError, match="returned no content"):
        async for _ in service.answer_question_stream("What is Redis?", _sample_passages()):
            pass


@pytest.mark.asyncio
async def test_openai_transport_errors_are_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    completions = _FakeOpenAIChatCompletions(error=OpenAIError("boom"))
    monkeypatch.setattr(
        "app.services.llm.openai_provider.AsyncOpenAI",
        lambda **kwargs: _FakeOpenAIClient(completions),
    )
    service = OpenAICompatibleLLMService(
        Settings(llm_provider="openai", llm_api_key="k", llm_model="gpt-test")
    )

    with pytest.raises(LLMInvocationError, match="request failed"):
        await service.answer_question("What is Redis?", _sample_passages())


@pytest.mark.asyncio
async def test_anthropic_structured_calls_parse_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    messages = _FakeAnthropicMessages(
        contents=['{"summary":"hello","bullets":["one"]}']
    )
    monkeypatch.setattr(
        "app.services.llm.anthropic_provider.AsyncAnthropic",
        lambda **kwargs: _FakeAnthropicClient(messages),
    )
    service = AnthropicLLMService(
        Settings(llm_provider="anthropic", llm_api_key="k", llm_model="claude-test")
    )

    out = await service.summarize_chunk("chunk text", "brief")
    assert out.summary == "hello"
    assert out.bullets == ["one"]


@pytest.mark.asyncio
async def test_anthropic_structured_calls_fallback_after_invalid_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages = _FakeAnthropicMessages(contents=["", "not json", "{still broken"])
    invalid_logs: list[dict] = []
    monkeypatch.setattr(
        "app.services.llm.anthropic_provider.AsyncAnthropic",
        lambda **kwargs: _FakeAnthropicClient(messages),
    )
    monkeypatch.setattr(
        "app.services.llm.provider_support.log_llm_invalid_output",
        lambda **kwargs: invalid_logs.append(kwargs),
    )
    service = AnthropicLLMService(
        Settings(llm_provider="anthropic", llm_api_key="k", llm_model="claude-test")
    )

    payload = await service.generate_study_notes("prompt")
    assert payload.concise_notes == ""
    assert payload.detailed_notes == ""
    assert payload.glossary_terms == []
    assert len(messages.calls) == 3
    assert len(invalid_logs) == 3
    assert invalid_logs[-1]["fallback_used"] is True


@pytest.mark.asyncio
async def test_anthropic_stream_raises_on_transport_error(monkeypatch: pytest.MonkeyPatch) -> None:
    messages = _FakeAnthropicMessages(error=AnthropicError("boom"))
    monkeypatch.setattr(
        "app.services.llm.anthropic_provider.AsyncAnthropic",
        lambda **kwargs: _FakeAnthropicClient(messages),
    )
    service = AnthropicLLMService(
        Settings(llm_provider="anthropic", llm_api_key="k", llm_model="claude-test")
    )

    with pytest.raises(LLMInvocationError, match="request failed"):
        async for _ in service.answer_question_stream("What is Redis?", _sample_passages()):
            pass


@pytest.mark.asyncio
async def test_openai_answer_question_returns_structured_qa_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completions = _FakeOpenAIChatCompletions(
        contents=['{"answer":"Redis is used as a cache."}']
    )
    monkeypatch.setattr(
        "app.services.llm.openai_provider.AsyncOpenAI",
        lambda **kwargs: _FakeOpenAIClient(completions),
    )
    service = OpenAICompatibleLLMService(
        Settings(llm_provider="openai", llm_api_key="k", llm_model="gpt-test")
    )

    payload = await service.answer_question("What is Redis?", _sample_passages())
    assert isinstance(payload, QAResponse)
    assert payload.answer == "Redis is used as a cache."


@pytest.mark.asyncio
async def test_openai_records_real_token_usage_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completions = _FakeOpenAIChatCompletions(
        contents=['{"summary":"hello","bullets":["one"]}'],
        usages=[SimpleNamespace(prompt_tokens=11, completion_tokens=7, total_tokens=18)],
    )
    usage_events: list[dict] = []
    monkeypatch.setattr(
        "app.services.llm.openai_provider.AsyncOpenAI",
        lambda **kwargs: _FakeOpenAIClient(completions),
    )
    monkeypatch.setattr(
        "app.services.llm.provider_support.record_llm_usage",
        lambda **kwargs: usage_events.append(kwargs),
    )

    service = OpenAICompatibleLLMService(
        Settings(llm_provider="openai", llm_api_key="k", llm_model="gpt-test")
    )
    await service.summarize_chunk("chunk text", "brief")

    assert len(usage_events) == 1
    metrics = usage_events[0]["metrics"]
    assert metrics.input_tokens == 11
    assert metrics.output_tokens == 7
    assert metrics.total_tokens == 18


@pytest.mark.parametrize("provider_name", ["mock", "openai", "anthropic"])
@pytest.mark.asyncio
async def test_provider_parity_generate_study_notes(provider_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    if provider_name == "mock":
        service = MockLLMService()
    elif provider_name == "openai":
        completions = _FakeOpenAIChatCompletions(
            contents=[
                '{"concise_notes":"short","detailed_notes":"long","glossary_terms":[{"term":"Redis","definition":"cache"}]}'
            ]
        )
        monkeypatch.setattr(
            "app.services.llm.openai_provider.AsyncOpenAI",
            lambda **kwargs: _FakeOpenAIClient(completions),
        )
        service = OpenAICompatibleLLMService(
            Settings(llm_provider="openai", llm_api_key="k", llm_model="gpt-test")
        )
    else:
        messages = _FakeAnthropicMessages(
            contents=[
                '{"concise_notes":"short","detailed_notes":"long","glossary_terms":[{"term":"Redis","definition":"cache"}]}'
            ]
        )
        monkeypatch.setattr(
            "app.services.llm.anthropic_provider.AsyncAnthropic",
            lambda **kwargs: _FakeAnthropicClient(messages),
        )
        service = AnthropicLLMService(
            Settings(llm_provider="anthropic", llm_api_key="k", llm_model="claude-test")
        )

    payload = await service.generate_study_notes("prompt")
    assert isinstance(payload.concise_notes, str)
    assert isinstance(payload.detailed_notes, str)
    assert isinstance(payload.glossary_terms, list)


@pytest.mark.parametrize("provider_name", ["mock", "openai", "anthropic"])
@pytest.mark.asyncio
async def test_provider_parity_query_understanding(provider_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    if provider_name == "mock":
        service = MockLLMService()
    elif provider_name == "openai":
        completions = _FakeOpenAIChatCompletions(
            contents=[
                '{"intent":"definition","normalized_query":"what is redis","expansion_keywords":["cache"]}'
            ]
        )
        monkeypatch.setattr(
            "app.services.llm.openai_provider.AsyncOpenAI",
            lambda **kwargs: _FakeOpenAIClient(completions),
        )
        service = OpenAICompatibleLLMService(
            Settings(llm_provider="openai", llm_api_key="k", llm_model="gpt-test")
        )
    else:
        messages = _FakeAnthropicMessages(
            contents=[
                '{"intent":"definition","normalized_query":"what is redis","expansion_keywords":["cache"]}'
            ]
        )
        monkeypatch.setattr(
            "app.services.llm.anthropic_provider.AsyncAnthropic",
            lambda **kwargs: _FakeAnthropicClient(messages),
        )
        service = AnthropicLLMService(
            Settings(llm_provider="anthropic", llm_api_key="k", llm_model="claude-test")
        )

    payload = await service.understand_qa_query("What is Redis?")
    assert payload.intent in {"definition", "factual", "conceptual", "comparison"}
    assert isinstance(payload.normalized_query, str)
    assert isinstance(payload.expansion_keywords, list)


@pytest.mark.asyncio
async def test_provider_parity_context_compression(monkeypatch: pytest.MonkeyPatch) -> None:
    hits = _sample_hits()

    openai_completions = _FakeOpenAIChatCompletions(
        contents=[
            '{"items":[{"summary":"(00:12-00:25) compressed context","source_chunk_indices":[0,1,2],"time_start_seconds":12.0,"time_end_seconds":25.0},{"summary":"(00:12) repeated context","source_chunk_indices":[0],"time_start_seconds":12.0},{"summary":"(00:18) repeated context","source_chunk_indices":[1],"time_start_seconds":18.0}]}'
        ]
    )
    anthropic_messages = _FakeAnthropicMessages(
        contents=[
            '{"items":[{"summary":"(00:12-00:25) compressed context","source_chunk_indices":[0,1,2],"time_start_seconds":12.0,"time_end_seconds":25.0},{"summary":"(00:12) repeated context","source_chunk_indices":[0],"time_start_seconds":12.0},{"summary":"(00:18) repeated context","source_chunk_indices":[1],"time_start_seconds":18.0}]}'
        ]
    )
    monkeypatch.setattr(
        "app.services.llm.openai_provider.AsyncOpenAI",
        lambda **kwargs: _FakeOpenAIClient(openai_completions),
    )
    monkeypatch.setattr(
        "app.services.llm.anthropic_provider.AsyncAnthropic",
        lambda **kwargs: _FakeAnthropicClient(anthropic_messages),
    )

    providers = [
        MockLLMService(),
        OpenAICompatibleLLMService(Settings(llm_provider="openai", llm_api_key="k", llm_model="gpt-test")),
        AnthropicLLMService(Settings(llm_provider="anthropic", llm_api_key="k", llm_model="claude-test")),
    ]

    for provider in providers:
        payload = await provider.compress_qa_retrieval_context("What is Redis?", hits, 3)
        assert len(payload.items) >= 1
        assert all(item.source_chunk_indices for item in payload.items)

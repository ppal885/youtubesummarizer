from types import SimpleNamespace

import pytest

from app.config import Settings
from app.models.qa_models import TranscriptChunkPassage
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
    ) -> None:
        self.contents = list(contents or [])
        self.stream_chunks = list(stream_chunks or [])
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            chunks = [
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content=chunk))]
                )
                for chunk in self.stream_chunks
            ]
            return _AsyncListIter(chunks)
        content = self.contents.pop(0) if self.contents else None
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=None,
        )


class _FakeOpenAIClient:
    def __init__(self, completions: _FakeOpenAIChatCompletions) -> None:
        self.chat = SimpleNamespace(completions=completions)


def _sample_passages() -> list[TranscriptChunkPassage]:
    return [
        TranscriptChunkPassage(
            id=1,
            chunk_index=0,
            start_seconds=12.0,
            text="Redis is used as a cache in this segment.",
        )
    ]


def test_in_memory_prompt_cache_expires_after_ttl() -> None:
    now = {"value": 100.0}
    cache = InMemoryPromptCache(default_ttl_seconds=5.0, now_fn=lambda: now["value"])

    cache.set("prompt", "response")
    assert cache.get("prompt")[0] == "response"

    now["value"] = 106.0
    assert cache.get("prompt")[0] is None


@pytest.mark.asyncio
async def test_structured_completion_uses_prompt_cache(monkeypatch) -> None:
    cache = InMemoryPromptCache()
    completions = _FakeOpenAIChatCompletions(
        contents=['{"summary":"hello","bullets":["one"]}']
    )
    cache_logs: list[dict] = []

    monkeypatch.setattr(
        "app.services.llm.provider_support.get_prompt_response_cache",
        lambda: cache,
    )
    monkeypatch.setattr(
        "app.services.llm.provider_support.log_llm_cache_event",
        lambda **kwargs: cache_logs.append(kwargs),
    )
    monkeypatch.setattr(
        "app.services.llm.openai_provider.AsyncOpenAI",
        lambda **kwargs: _FakeOpenAIClient(completions),
    )

    service = OpenAICompatibleLLMService(
        Settings(llm_provider="openai", llm_api_key="k", llm_model="gpt-test")
    )

    first = await service.summarize_chunk("chunk text", "brief")
    second = await service.summarize_chunk("chunk text", "brief")

    assert first.summary == "hello"
    assert second.summary == "hello"
    assert len(completions.calls) == 1
    assert [log["hit"] for log in cache_logs] == [False, True]


@pytest.mark.asyncio
async def test_stream_completion_uses_prompt_cache(monkeypatch) -> None:
    cache = InMemoryPromptCache()
    completions = _FakeOpenAIChatCompletions(stream_chunks=["hello", " world"])
    cache_logs: list[dict] = []

    monkeypatch.setattr(
        "app.services.llm.provider_support.get_prompt_response_cache",
        lambda: cache,
    )
    monkeypatch.setattr(
        "app.services.llm.provider_support.log_llm_cache_event",
        lambda **kwargs: cache_logs.append(kwargs),
    )
    monkeypatch.setattr(
        "app.services.llm.openai_provider.AsyncOpenAI",
        lambda **kwargs: _FakeOpenAIClient(completions),
    )

    service = OpenAICompatibleLLMService(
        Settings(llm_provider="openai", llm_api_key="k", llm_model="gpt-test")
    )

    async def _collect(ait):
        parts: list[str] = []
        async for frag in ait:
            parts.append(frag)
        return "".join(parts)

    first = await _collect(service.answer_question_stream("What is Redis?", _sample_passages()))
    second = await _collect(service.answer_question_stream("What is Redis?", _sample_passages()))

    assert first == "hello world"
    assert second == "hello world"
    assert len(completions.calls) == 1
    assert [log["hit"] for log in cache_logs] == [False, True]

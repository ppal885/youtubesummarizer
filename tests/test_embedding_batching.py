import pytest

from app.config import Settings
from app.exceptions import EmbeddingInvocationError
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.factory import get_embedding_service
from app.services.embeddings.service import EmbeddingService


class _RecordingEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    @property
    def dimension(self) -> int:
        return 1

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[float(text.split("-")[-1])] if "-" in text else [float(ord(text[0]))] for text in texts]


class _ShortEmbeddingProvider(EmbeddingProvider):
    @property
    def dimension(self) -> int:
        return 1

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] for _ in texts[:-1]]


def test_embedding_service_batches_texts_and_preserves_order() -> None:
    provider = _RecordingEmbeddingProvider()
    service = EmbeddingService(provider, batch_size=2)

    vectors = service.embed(["chunk-1", "chunk-2", "chunk-3", "chunk-4", "chunk-5"])

    assert provider.calls == [["chunk-1", "chunk-2"], ["chunk-3", "chunk-4"], ["chunk-5"]]
    assert vectors == [[1.0], [2.0], [3.0], [4.0], [5.0]]


def test_embedding_service_raises_when_batch_mapping_breaks() -> None:
    service = EmbeddingService(_ShortEmbeddingProvider(), batch_size=3)

    with pytest.raises(EmbeddingInvocationError, match="Embedding batch returned"):
        service.embed(["a", "b", "c"])


def test_get_embedding_service_uses_configured_batch_size(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _RecordingEmbeddingProvider()
    monkeypatch.setattr(
        "app.services.embeddings.factory.get_embedding_provider",
        lambda settings: provider,
    )
    service = get_embedding_service(Settings(embedding_provider="mock", embedding_batch_size=3))

    vectors = service.embed(["a", "b", "c", "d"])

    assert provider.calls == [["a", "b", "c"], ["d"]]
    assert vectors == [[97.0], [98.0], [99.0], [100.0]]


def test_embedding_service_splits_batches_by_char_budget() -> None:
    provider = _RecordingEmbeddingProvider()
    service = EmbeddingService(provider, batch_size=10, max_chars_per_batch=5)

    service.embed(["ab", "cd", "efgh"])

    assert provider.calls == [["ab", "cd"], ["efgh"]]


def test_embedding_service_sends_oversized_string_in_its_own_batch() -> None:
    provider = _RecordingEmbeddingProvider()
    service = EmbeddingService(provider, batch_size=10, max_chars_per_batch=5)

    service.embed(["abcdef", "x"])

    assert provider.calls == [["abcdef"], ["x"]]


def test_embed_paired_preserves_text_vector_mapping() -> None:
    provider = _RecordingEmbeddingProvider()
    service = EmbeddingService(provider, batch_size=2)

    pairs = service.embed_paired(["chunk-1", "chunk-2", "chunk-3"])

    assert pairs == [("chunk-1", [1.0]), ("chunk-2", [2.0]), ("chunk-3", [3.0])]


def test_get_embedding_service_passes_max_chars_per_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _RecordingEmbeddingProvider()
    monkeypatch.setattr(
        "app.services.embeddings.factory.get_embedding_provider",
        lambda settings: provider,
    )
    service = get_embedding_service(
        Settings(
            embedding_provider="mock",
            embedding_batch_size=10,
            embedding_max_chars_per_batch=3,
        )
    )
    service.embed(["a", "bc", "d"])

    assert provider.calls == [["a", "bc"], ["d"]]

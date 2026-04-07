from __future__ import annotations

from app.exceptions import EmbeddingInvocationError
from app.services.embeddings.base import EmbeddingProvider


class EmbeddingService(EmbeddingProvider):
    """Provider-agnostic batching facade for text embeddings."""

    def __init__(self, provider: EmbeddingProvider, *, batch_size: int = 64) -> None:
        self._provider = provider
        self._batch_size = max(1, int(batch_size))

    @property
    def dimension(self) -> int:
        return self._provider.dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            batch_vectors = self._provider.embed(batch)
            if len(batch_vectors) != len(batch):
                raise EmbeddingInvocationError(
                    f"Embedding batch returned {len(batch_vectors)} vectors for {len(batch)} texts."
                )
            vectors.extend(batch_vectors)
        return vectors

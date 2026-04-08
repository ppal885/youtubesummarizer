from __future__ import annotations

from app.exceptions import EmbeddingInvocationError
from app.services.embeddings.base import EmbeddingProvider


def _batch_slice_boundaries(
    texts: list[str],
    *,
    max_items: int,
    max_chars: int,
) -> list[tuple[int, int]]:
    """
    Partition ``range(len(texts))`` into [lo, hi) slices for provider calls.

    Each slice has at most ``max_items`` strings. When ``max_chars > 0``, cumulative
    ``sum(len(texts[j]) for j in range(lo, hi))`` is at most ``max_chars`` (except a
    single oversized string is sent alone).
    """
    n = len(texts)
    if n == 0:
        return []
    max_items = max(1, int(max_items))
    out: list[tuple[int, int]] = []
    lo = 0
    while lo < n:
        if max_chars <= 0:
            hi = min(lo + max_items, n)
            out.append((lo, hi))
            lo = hi
            continue
        hi = lo
        batch_chars = 0
        items = 0
        while hi < n and items < max_items:
            tlen = len(texts[hi])
            if items > 0 and batch_chars + tlen > max_chars:
                break
            batch_chars += tlen
            items += 1
            hi += 1
            if batch_chars >= max_chars:
                break
        if hi == lo:
            hi = lo + 1
        out.append((lo, hi))
        lo = hi
    return out


class EmbeddingService(EmbeddingProvider):
    """
    Provider-agnostic facade: splits inputs into few provider calls while preserving order.

    For input ``texts``, output ``vectors`` has ``len(vectors) == len(texts)`` and
    ``vectors[i]`` is the embedding for ``texts[i]`` (stable across batch boundaries).
    """

    def __init__(
        self,
        provider: EmbeddingProvider,
        *,
        batch_size: int = 64,
        max_chars_per_batch: int = 0,
    ) -> None:
        self._provider = provider
        self._batch_size = max(1, int(batch_size))
        self._max_chars_per_batch = max(0, int(max_chars_per_batch))

    @property
    def dimension(self) -> int:
        return self._provider.dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        boundaries = _batch_slice_boundaries(
            texts,
            max_items=self._batch_size,
            max_chars=self._max_chars_per_batch,
        )
        vectors: list[list[float]] = []
        for lo, hi in boundaries:
            batch = texts[lo:hi]
            batch_vectors = self._provider.embed(batch)
            if len(batch_vectors) != len(batch):
                raise EmbeddingInvocationError(
                    f"Embedding batch returned {len(batch_vectors)} vectors for {len(batch)} texts."
                )
            vectors.extend(batch_vectors)
        return vectors

    def embed_paired(self, texts: list[str]) -> list[tuple[str, list[float]]]:
        """Same as :meth:`embed`, but returns explicit ``(text, vector)`` pairs in input order."""
        out_vectors = self.embed(texts)
        return list(zip(texts, out_vectors, strict=True))

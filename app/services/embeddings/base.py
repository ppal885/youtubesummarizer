from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """
    Provider-agnostic text embeddings.

    Implementations used with FAISS IndexFlatIP + cosine similarity should return
    L2-normalized vectors so inner product equals cosine similarity.
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Fixed embedding size for all outputs from this provider."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts in a single provider call when possible.

        Implementations receive slices produced by :class:`~app.services.embeddings.service.EmbeddingService`
        (count- and optionally size-limited batches). Each call must return one vector per input,
        in the same order as ``texts``.
        """

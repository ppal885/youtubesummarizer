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
        Embed each non-empty text; empty strings may yield zero vectors or raise.

        Returns one vector per input, same length as ``texts``.
        """

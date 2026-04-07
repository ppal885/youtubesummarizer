import math

from openai import OpenAI, OpenAIError

from app.config import Settings
from app.db.constants import VECTOR_STORAGE_DIMENSIONS
from app.exceptions import EmbeddingConfigurationError, EmbeddingInvocationError
from app.services.embeddings.base import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI ``embeddings.create`` (or compatible base_url)."""

    def __init__(self, settings: Settings) -> None:
        api_key = (settings.embedding_api_key or settings.llm_api_key).strip()
        if not api_key:
            raise EmbeddingConfigurationError(
                "EMBEDDING_PROVIDER is 'openai' but neither EMBEDDING_API_KEY nor LLM_API_KEY is set."
            )
        base_url = settings.llm_base_url.strip() or None
        self._model = settings.embedding_model
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=settings.llm_timeout_seconds)
        self._dim: int | None = None

    @property
    def dimension(self) -> int:
        if self._dim is None:
            raise EmbeddingInvocationError("OpenAI embedding dimension is unknown until the first embed call.")
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = self._client.embeddings.create(model=self._model, input=texts)
        except OpenAIError as exc:
            raise EmbeddingInvocationError(f"OpenAI embeddings request failed: {exc}") from exc

        data = sorted(response.data, key=lambda d: d.index)
        if len(data) != len(texts):
            raise EmbeddingInvocationError(
                f"Expected {len(texts)} embedding rows, got {len(data)}."
            )

        out: list[list[float]] = []
        for row in data:
            vec = [float(x) for x in row.embedding]
            if len(vec) != VECTOR_STORAGE_DIMENSIONS:
                raise EmbeddingInvocationError(
                    f"Embedding dimension {len(vec)} does not match VECTOR_STORAGE_DIMENSIONS="
                    f"{VECTOR_STORAGE_DIMENSIONS} (text-embedding-3-small default). "
                    "Adjust your embedding model or VECTOR_STORAGE_DIMENSIONS in code."
                )
            if self._dim is None:
                self._dim = len(vec)
            elif len(vec) != self._dim:
                raise EmbeddingInvocationError("Inconsistent embedding dimensions from API.")
            out.append(_normalize(vec))
        return out


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 0:
        return vec
    return [x / norm for x in vec]

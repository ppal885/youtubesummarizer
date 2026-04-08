from app.config import Settings
from app.exceptions import EmbeddingConfigurationError
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.mock_provider import MockEmbeddingProvider
from app.services.embeddings.openai_embeddings import OpenAIEmbeddingProvider
from app.services.embeddings.service import EmbeddingService


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    provider = settings.embedding_provider.lower().strip()
    if provider == "mock":
        return MockEmbeddingProvider(settings)
    if provider == "openai":
        return OpenAIEmbeddingProvider(settings)
    raise EmbeddingConfigurationError(
        f"Unsupported EMBEDDING_PROVIDER '{settings.embedding_provider}'. "
        "Supported values: mock, openai."
    )


def get_embedding_service(settings: Settings) -> EmbeddingService:
    return EmbeddingService(
        get_embedding_provider(settings),
        batch_size=settings.embedding_batch_size,
        max_chars_per_batch=settings.embedding_max_chars_per_batch,
    )

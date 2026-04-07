from app.config import Settings
from app.exceptions import UnsupportedRetrieverError
from app.services.retrieval.base import ChunkRetriever
from app.services.retrieval.embedding_retriever import EmbeddingChunkRetriever
from app.services.retrieval.mock_retriever import MockChunkRetriever


def get_chunk_retriever(settings: Settings) -> ChunkRetriever:
    """Factory for retrieval backends (mock lexical vs embedding-ready stub)."""
    provider = settings.retriever_provider.lower().strip()
    if provider == "mock":
        return MockChunkRetriever(settings)
    if provider == "embedding":
        return EmbeddingChunkRetriever(settings)
    raise UnsupportedRetrieverError(settings.retriever_provider)

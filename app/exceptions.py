"""Domain-level errors surfaced to HTTP handlers."""


class InvalidYouTubeUrlError(ValueError):
    """The request URL is not a supported YouTube video link."""


class TranscriptFetchError(RuntimeError):
    """Captions could not be loaded or were unusable after processing."""


class UnsupportedLLMProviderError(ValueError):
    """No implementation is registered for the configured LLM provider."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(
            f"Unsupported LLM_PROVIDER '{provider}'. "
            "Supported values: mock, openai, anthropic."
        )


class LLMConfigurationError(ValueError):
    """LLM is selected but required settings (for example an API key) are missing."""

    pass


class LLMInvocationError(RuntimeError):
    """The configured LLM provider failed or returned an unusable response."""

    pass


class BackendWorkflowError(RuntimeError):
    """An internal orchestration workflow could not produce a valid result."""

    pass


class DatabaseConfigurationError(ValueError):
    """Database URL or engine does not meet requirements (e.g. pgvector needs PostgreSQL)."""

    pass


class EmbeddingConfigurationError(ValueError):
    """Embedding provider is selected but required settings (e.g. API key) are missing."""

    pass


class EmbeddingInvocationError(RuntimeError):
    """Embedding provider failed or returned vectors of unexpected shape."""

    pass


class UnsupportedRetrieverError(ValueError):
    """No implementation is registered for the configured retriever provider."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(
            f"Unsupported RETRIEVER_PROVIDER '{provider}'. "
            "Supported values: mock (lexical), embedding (PostgreSQL pgvector)."
        )

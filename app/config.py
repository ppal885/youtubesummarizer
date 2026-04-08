from typing import Self

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="YouTube Video Copilot", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_timeout_seconds: float = Field(
        default=120.0,
        ge=5.0,
        le=600.0,
        alias="LLM_TIMEOUT_SECONDS",
        description="HTTP read timeout for outbound LLM calls (summaries can be slow).",
    )
    llm_json_response_format: bool = Field(
        default=True,
        alias="LLM_JSON_RESPONSE_FORMAT",
        description="If true, OpenAI-compatible calls use response_format json_object. "
        "Set false for some local servers (Ollama/LM Studio) that reject it.",
    )
    max_chunk_chars: int = Field(default=4000, ge=256, alias="MAX_CHUNK_CHARS")
    chunk_overlap_chars: int = Field(default=200, ge=0, alias="CHUNK_OVERLAP_CHARS")
    chunk_use_tokens: bool = Field(default=False, alias="CHUNK_USE_TOKENS")
    chunk_token_encoding: str = Field(default="cl100k_base", alias="CHUNK_TOKEN_ENCODING")
    max_chunk_tokens: int = Field(default=900, ge=32, alias="MAX_CHUNK_TOKENS")
    chunk_overlap_tokens: int = Field(default=120, ge=0, alias="CHUNK_OVERLAP_TOKENS")
    database_url: str = Field(
        default="sqlite:///./summaries.db",
        alias="DATABASE_URL",
        description="SQLAlchemy URL; default is local SQLite file summaries.db",
    )
    retriever_provider: str = Field(
        default="mock",
        alias="RETRIEVER_PROVIDER",
        description="mock: lexical overlap; embedding: PostgreSQL pgvector (requires Postgres + extension).",
    )
    qa_retrieval_pool: int = Field(
        default=10,
        ge=1,
        le=32,
        validation_alias=AliasChoices("QA_RETRIEVAL_POOL", "QA_TOP_K"),
        description="Wide retrieval pool before RAG context compression (legacy env: QA_TOP_K).",
    )
    qa_context_compress_to: int = Field(
        default=4,
        ge=3,
        le=5,
        alias="QA_CONTEXT_COMPRESS_TO",
        description="Target number of context blocks passed to the answer LLM after compression.",
    )
    qa_context_compression: str = Field(
        default="heuristic",
        alias="QA_CONTEXT_COMPRESSION",
        description="heuristic: merge/rank-local compression; llm: one structured compression call.",
    )
    embedding_provider: str = Field(
        default="mock",
        alias="EMBEDDING_PROVIDER",
        description="mock: deterministic local vectors; openai: OpenAI embeddings API.",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="EMBEDDING_MODEL",
        description="Model id for OpenAI embeddings (ignored for mock).",
    )
    embedding_api_key: str = Field(
        default="",
        alias="EMBEDDING_API_KEY",
        description="Optional; defaults to LLM_API_KEY when empty and provider is openai.",
    )
    embedding_dimensions: int = Field(
        default=1536,
        ge=32,
        le=3072,
        alias="EMBEDDING_DIMENSIONS",
        description="Must match pgvector column size (1536 for text-embedding-3-small). Used by mock provider.",
    )
    embedding_batch_size: int = Field(
        default=128,
        ge=1,
        le=2048,
        alias="EMBEDDING_BATCH_SIZE",
        description="Maximum number of texts to send in one embedding provider call.",
    )
    embedding_max_chars_per_batch: int = Field(
        default=0,
        ge=0,
        alias="EMBEDDING_MAX_CHARS_PER_BATCH",
        description="If > 0, also split batches when cumulative input character length would exceed "
        "this value (provider-agnostic; 0 = item-count batching only).",
    )
    retrieval_hybrid_alpha: float = Field(
        default=0.65,
        ge=0,
        alias="RETRIEVAL_HYBRID_ALPHA",
        description="Weight for normalized semantic (embedding) similarity in hybrid ranking.",
    )
    retrieval_hybrid_beta: float = Field(
        default=0.35,
        ge=0,
        alias="RETRIEVAL_HYBRID_BETA",
        description="Weight for normalized BM25-style keyword score in hybrid ranking.",
    )
    cors_origins: str = Field(
        default=(
            "http://127.0.0.1:5174,http://localhost:5174,"
            "http://127.0.0.1:5173,http://localhost:5173"
        ),
        alias="CORS_ORIGINS",
        description="Comma-separated browser origins allowed for CORS (e.g. Vite dev server).",
    )
    demo_mode: bool = Field(
        default=False,
        alias="DEMO_MODE",
        description="When true, a fixed sample video uses precomputed summary and Q&A (no YouTube/LLM).",
    )
    rate_limit_enabled: bool = Field(
        default=False,
        alias="RATE_LIMIT_ENABLED",
        description="When true, apply in-memory sliding-window limits per user on /api/* routes.",
    )
    rate_limit_requests_per_minute: int = Field(
        default=60,
        ge=1,
        le=100_000,
        alias="RATE_LIMIT_REQUESTS_PER_MINUTE",
        description="Max HTTP requests per user per minute (sliding window).",
    )

    @field_validator("qa_context_compression", mode="before")
    @classmethod
    def normalize_qa_context_compression(cls, v: object) -> str:
        if v is None:
            return "heuristic"
        s = str(v).strip().lower()
        if s not in ("heuristic", "llm"):
            raise ValueError("QA_CONTEXT_COMPRESSION must be 'heuristic' or 'llm'.")
        return s

    @model_validator(mode="after")
    def validate_settings_constraints(self) -> Self:
        if self.chunk_overlap_chars >= self.max_chunk_chars:
            raise ValueError("CHUNK_OVERLAP_CHARS must be less than MAX_CHUNK_CHARS")
        if self.chunk_use_tokens and self.chunk_overlap_tokens >= self.max_chunk_tokens:
            raise ValueError("CHUNK_OVERLAP_TOKENS must be less than MAX_CHUNK_TOKENS")
        if self.retrieval_hybrid_alpha == 0 and self.retrieval_hybrid_beta == 0:
            raise ValueError(
                "RETRIEVAL_HYBRID_ALPHA and RETRIEVAL_HYBRID_BETA cannot both be 0 (hybrid ranking would be undefined)."
            )
        if self.qa_context_compress_to > self.qa_retrieval_pool:
            raise ValueError(
                "QA_CONTEXT_COMPRESS_TO cannot exceed QA_RETRIEVAL_POOL / QA_TOP_K (cannot compress to more blocks than retrieved)."
            )
        return self


settings = Settings()

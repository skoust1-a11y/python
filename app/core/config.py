"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.mcp.models import MCPServerConfig, parse_mcp_servers


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "C3 LegalDoc Navigator"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: str = "change-me"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://legaldoc:legaldoc_secret@localhost:5432/legaldoc_navigator"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://legaldoc:legaldoc_secret@localhost:5432/legaldoc_navigator"

    # Vector store
    VECTOR_DIMENSION: int = 1536
    VECTOR_TABLE_NAME: str = "document_embeddings"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_CHAT_MODEL: str = "claude-3-5-sonnet-20241022"

    # LLM routing
    DEFAULT_LLM_PROVIDER: str = "openai"
    FALLBACK_LLM_PROVIDER: str = "anthropic"

    # RAG — legal chunking (token-based via tiktoken cl100k_base)
    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 100
    TOP_K_RETRIEVAL: int = 5
    SIMILARITY_THRESHOLD: float = 0.7

    # Ingestion
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list[str] = ["pdf", "docx", "txt"]

    # Guardrails
    ENABLE_GUARDRAILS: bool = True
    MAX_QUERY_LENGTH: int = 2000

    # Human handoff
    HANDOFF_CONFIDENCE_THRESHOLD: float = 0.70

    # Langfuse observability
    ENABLE_LANGFUSE: bool = False
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # RAG evaluation
    EVAL_OUTPUT_DIR: str = "./data/evaluation/results"
    EVAL_BENCHMARK_PATH: str = "./data/evaluation/benchmark.json"
    EVAL_RAGAS_MODEL: str = "gpt-4o-mini"
    EVAL_LATENCY_THRESHOLD_MS: float = 5000.0
    EVAL_COST_THRESHOLD_USD: float = 0.05

    # External legal databases (MCP)
    MCP_ENABLED: bool = False
    MCP_SEARCH_TIMEOUT_SECONDS: float = 30.0
    MCP_RETRY_MAX_ATTEMPTS: int = 3
    MCP_RETRY_MIN_WAIT_SECONDS: float = 1.0
    MCP_RETRY_MAX_WAIT_SECONDS: float = 10.0
    MCP_SERVERS: list[MCPServerConfig] = []

    @field_validator("MCP_SERVERS", mode="before")
    @classmethod
    def _parse_mcp_servers(cls, value: Any) -> list[MCPServerConfig]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            if not value:
                return []
            if isinstance(value[0], MCPServerConfig):
                return value
            return parse_mcp_servers(value)  # type: ignore[arg-type]
        if isinstance(value, str):
            return parse_mcp_servers(value)
        raise ValueError("MCP_SERVERS must be a JSON array or list of server configs.")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

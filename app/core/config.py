"""Application settings loaded from environment variables.

Values live in `.env` (or the process environment). This module defines the
schema, types, validation, and a single `settings` object for the rest of the app.
Set variables in `.env`; see `.env.example` for the full list.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Self
from urllib.parse import quote_plus

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.mcp.models import MCPServerConfig, parse_mcp_servers


def _build_postgres_url(
    *,
    driver: str,
    user: str,
    password: str,
    host: str,
    port: int,
    database: str,
) -> str:
    user_enc = quote_plus(user)
    auth = f"{user_enc}:{quote_plus(password)}@" if password else f"{user_enc}@"
    return f"postgresql+{driver}://{auth}{host}:{port}/{database}"


def _normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower().replace("-", "_")
    aliases = {
        "gemini": "google",
        "google_genai": "google",
        "azure": "azureopenai",
        "azure_openai": "azureopenai",
    }
    return aliases.get(normalized, normalized)


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
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]

    # PostgreSQL — set DATABASE_URL directly, or leave empty and use POSTGRES_* below
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "legaldoc"
    POSTGRES_PASSWORD: str = "legaldoc_secret"
    POSTGRES_DB: str = "legaldoc_navigator"
    DATABASE_URL: str = ""
    DATABASE_SYNC_URL: str = ""

    # Vector store
    VECTOR_DIMENSION: int = 1536
    VECTOR_TABLE_NAME: str = "document_embeddings"

    # -------------------------------------------------------------------------
    # LLM & embeddings — loaded from `.env` only (no defaults here).
    # Edit keys, models, and EMBEDDING_PROVIDER / DEFAULT_LLM_PROVIDER in `.env`.
    # -------------------------------------------------------------------------

    OPENAI_API_KEY: str = Field(default="", description="Set OPENAI_API_KEY in .env")
    OPENAI_EMBEDDING_MODEL: str = Field(default="", description="Set OPENAI_EMBEDDING_MODEL in .env")
    OPENAI_CHAT_MODEL: str = Field(default="", description="Set OPENAI_CHAT_MODEL in .env")

    ANTHROPIC_API_KEY: str = Field(default="", description="Set ANTHROPIC_API_KEY in .env")
    ANTHROPIC_CHAT_MODEL: str = Field(default="", description="Set ANTHROPIC_CHAT_MODEL in .env")

    GEMINI_API_KEY: str = Field(default="", description="Set GEMINI_API_KEY in .env")
    GEMINI_CHAT_MODEL: str = Field(default="", description="Set GEMINI_CHAT_MODEL in .env")
    GEMINI_EMBEDDING_MODEL: str = Field(default="", description="Set GEMINI_EMBEDDING_MODEL in .env")

    GROQ_API_KEY: str = Field(default="", description="Set GROQ_API_KEY in .env")
    GROQ_CHAT_MODEL: str = Field(default="", description="Set GROQ_CHAT_MODEL in .env")

    AZURE_OPENAI_API_KEY: str = Field(default="", description="Set AZURE_OPENAI_API_KEY in .env")
    AZURE_OPENAI_ENDPOINT: str = Field(default="", description="Set AZURE_OPENAI_ENDPOINT in .env")
    AZURE_OPENAI_API_VERSION: str = Field(default="", description="Set AZURE_OPENAI_API_VERSION in .env")
    AZURE_OPENAI_DEPLOYMENT: str = Field(default="", description="Set AZURE_OPENAI_DEPLOYMENT in .env")
    AZURE_OPENAI_CHAT_MODEL: str = Field(default="", description="Set AZURE_OPENAI_CHAT_MODEL in .env")

    EMBEDDING_PROVIDER: str = Field(default="", description="Set EMBEDDING_PROVIDER in .env (openai | google | gemini)")
    DEFAULT_LLM_PROVIDER: str = Field(default="", description="Set DEFAULT_LLM_PROVIDER in .env")
    FALLBACK_LLM_PROVIDER: str = Field(default="", description="Set FALLBACK_LLM_PROVIDER in .env")

    # RAG — legal chunking (token-based via tiktoken cl100k_base)
    CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 128
    TOP_K_RETRIEVAL: int = 5
    FINAL_TOP_K: int = 5
    RETRIEVAL_CANDIDATE_MULTIPLIER: int = 4
    SIMILARITY_THRESHOLD: float = 0.7
    SCOPED_SIMILARITY_THRESHOLD: float = 0.45
    SCOPED_TOP_K_RETRIEVAL: int = 10
    KEYWORD_TEXT_MATCH_BOOST: float = 0.03
    KEYWORD_METADATA_MATCH_BOOST: float = 0.05
    KEYWORD_BOOST_CAP: float = 0.20
    SAME_DOC_PRIMARY_BOOST: float = 0.08
    SAME_DOC_SECONDARY_BOOST: float = 0.03
    OVERLAP_MERGE_MIN_CHARS: int = 40
    OVERLAP_MERGE_MIN_RATIO: float = 0.12
    NEAR_DUPLICATE_JACCARD_THRESHOLD: float = 0.85

    # Context compression (pre-LLM prompt minimization)
    ENABLE_CONTEXT_COMPRESSION: bool = False
    MAX_CONTEXT_TOKENS: int = 6000
    CONTEXT_COMPRESSION_RELEVANCE_THRESHOLD: float = 0.15
    CONTEXT_COMPRESSION_NEAR_DUPLICATE_JACCARD_THRESHOLD: float = 0.90
    CONTEXT_COMPRESSION_MIN_SENTENCE_CHARS: int = 20

    # Ingestion
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list[str] = ["pdf", "docx", "txt"]

    # Guardrails
    ENABLE_GUARDRAILS: bool = True
    MAX_QUERY_LENGTH: int = 2000
    GUARDRAILS_RUN_SYNC: bool = True

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

    @model_validator(mode="after")
    def _validate_llm_settings(self) -> Self:
        errors: list[str] = []

        def require(provider: str, role: str) -> None:
            if not provider.strip():
                errors.append(f"Set {role} in .env (e.g. openai, google, anthropic)")
                return

            normalized = _normalize_provider(provider)
            if normalized == "openai":
                if not self.OPENAI_API_KEY.strip():
                    errors.append(f"{role}={provider} requires OPENAI_API_KEY in .env")
                if role == "EMBEDDING_PROVIDER":
                    if not self.OPENAI_EMBEDDING_MODEL.strip():
                        errors.append(f"{role}={provider} requires OPENAI_EMBEDDING_MODEL in .env")
                elif not self.OPENAI_CHAT_MODEL.strip():
                    errors.append(f"{role}={provider} requires OPENAI_CHAT_MODEL in .env")
            elif normalized == "google":
                if not self.GEMINI_API_KEY.strip():
                    errors.append(f"{role}={provider} requires GEMINI_API_KEY in .env")
                if role == "EMBEDDING_PROVIDER":
                    if not self.GEMINI_EMBEDDING_MODEL.strip():
                        errors.append(f"{role}={provider} requires GEMINI_EMBEDDING_MODEL in .env")
                elif not self.GEMINI_CHAT_MODEL.strip():
                    errors.append(f"{role}={provider} requires GEMINI_CHAT_MODEL in .env")
            elif normalized == "anthropic":
                if not self.ANTHROPIC_API_KEY.strip():
                    errors.append(f"{role}={provider} requires ANTHROPIC_API_KEY in .env")
                if not self.ANTHROPIC_CHAT_MODEL.strip():
                    errors.append(f"{role}={provider} requires ANTHROPIC_CHAT_MODEL in .env")
            elif normalized == "groq":
                if not self.GROQ_API_KEY.strip():
                    errors.append(f"{role}={provider} requires GROQ_API_KEY in .env")
                if not self.GROQ_CHAT_MODEL.strip():
                    errors.append(f"{role}={provider} requires GROQ_CHAT_MODEL in .env")
            elif normalized == "azureopenai":
                azure_fields = {
                    "AZURE_OPENAI_API_KEY": self.AZURE_OPENAI_API_KEY,
                    "AZURE_OPENAI_ENDPOINT": self.AZURE_OPENAI_ENDPOINT,
                    "AZURE_OPENAI_DEPLOYMENT": self.AZURE_OPENAI_DEPLOYMENT,
                    "AZURE_OPENAI_CHAT_MODEL": self.AZURE_OPENAI_CHAT_MODEL,
                    "AZURE_OPENAI_API_VERSION": self.AZURE_OPENAI_API_VERSION,
                }
                for key, value in azure_fields.items():
                    if not value.strip():
                        errors.append(f"{role}={provider} requires {key} in .env")
            else:
                errors.append(
                    f"Unknown {role}={provider!r} in .env "
                    "(use openai, google, anthropic, groq, or azureopenai)"
                )

        require(self.EMBEDDING_PROVIDER, "EMBEDDING_PROVIDER")
        require(self.DEFAULT_LLM_PROVIDER, "DEFAULT_LLM_PROVIDER")
        require(self.FALLBACK_LLM_PROVIDER, "FALLBACK_LLM_PROVIDER")

        if errors:
            raise ValueError("LLM configuration incomplete — update .env:\n- " + "\n- ".join(errors))
        return self

    @model_validator(mode="after")
    def _assemble_database_urls(self) -> Self:
        updates: dict[str, str] = {}
        if not self.DATABASE_URL.strip():
            updates["DATABASE_URL"] = _build_postgres_url(
                driver="asyncpg",
                user=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                database=self.POSTGRES_DB,
            )
        if not self.DATABASE_SYNC_URL.strip():
            updates["DATABASE_SYNC_URL"] = _build_postgres_url(
                driver="psycopg2",
                user=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                database=self.POSTGRES_DB,
            )
        if updates:
            return self.model_copy(update=updates)
        return self

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

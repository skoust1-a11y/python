"""Application settings loaded from environment variables.

Values live in `.env` (or the process environment). This module defines the
schema, types, validation, and a single `settings` object for the rest of the app.
Set variables in `.env`; see `.env.example` for the full list.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Self
from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.mcp.models import MCPServerConfig, parse_mcp_servers


def _strip_env_url(value: str) -> str:
    """Trim whitespace and optional wrapping quotes from env-provided URLs."""
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in "'\"":
        stripped = stripped[1:-1].strip()
    return stripped


def database_target_label(url: str, *, source: str = "DATABASE_URL") -> str:
    """Return a password-free connection label for logs and diagnostics."""
    from sqlalchemy.engine import make_url

    if not url.strip():
        return "<not configured>"

    parsed = make_url(url)
    host = parsed.host or "?"
    port = parsed.port or 5432
    database = parsed.database or "?"
    user = parsed.username or "?"
    return f"{source} -> {user}@{host}:{port}/{database}"


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


def _with_postgres_driver(url: str, driver: str) -> str:
    """Normalize hosted PostgreSQL URLs for SQLAlchemy async/sync engines."""
    stripped = url.strip()
    if not stripped:
        return ""
    if "://" not in stripped:
        return stripped

    scheme, rest = stripped.split("://", 1)
    if scheme in {"postgres", "postgresql"} or scheme.startswith("postgresql+"):
        return _normalize_postgres_ssl_query(f"postgresql+{driver}://{rest}", driver)
    return stripped


def _normalize_postgres_ssl_query(url: str, driver: str) -> str:
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    if not query:
        return url

    has_ssl = any(key == "ssl" for key, _value in query)
    has_sslmode = any(key == "sslmode" for key, _value in query)
    normalized: list[tuple[str, str]] = []
    for key, value in query:
        if driver == "asyncpg" and key in {"sslmode", "channel_binding"}:
            if key == "sslmode" and not has_ssl:
                normalized.append(("ssl", value))
            continue
        if driver == "psycopg2" and key == "ssl":
            if not has_sslmode:
                normalized.append(("sslmode", value))
            continue
        normalized.append((key, value))
    return urlunsplit(parts._replace(query=urlencode(normalized)))


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
    VECTOR_BACKEND: str = Field(default="pgvector", description="pgvector | qdrant")
    VECTOR_DIMENSION: int = 1536
    VECTOR_TABLE_NAME: str = "document_embeddings"

    # Qdrant (used when VECTOR_BACKEND=qdrant)
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "document_embeddings"

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

    # Evidence mode — minimum retrieval quality before showing extracted clauses
    EVIDENCE_RELEVANCE_THRESHOLD: float = 0.20
    EVIDENCE_MIN_CHUNK_SIMILARITY: float = 0.35
    EVIDENCE_QUERY_OVERLAP_THRESHOLD: float = 0.15

    # Response modes — set to true to re-enable Analysis mode LLM execution
    ENABLE_ANALYSIS_MODE: bool = False

    # BM25 keyword search
    BM25_DEFAULT_TOP_K: int = 10
    BM25_SNIPPET_MAX_CHARS: int = 400
    BM25_CACHE_MAX_ENTRIES: int = 8

    # Document search (/search) — independent from /query retrieval
    SEARCH_SEMANTIC_THRESHOLD: float = 0.55
    SEARCH_BM25_MIN_RAW_SCORE: float = 0.01
    SEARCH_CANDIDATE_POOL_MULTIPLIER: int = 3

    # Context compression (pre-LLM prompt minimization)
    ENABLE_CONTEXT_COMPRESSION: bool = False
    MAX_CONTEXT_TOKENS: int = 6000
    CONTEXT_COMPRESSION_RELEVANCE_THRESHOLD: float = 0.15
    CONTEXT_COMPRESSION_NEAR_DUPLICATE_JACCARD_THRESHOLD: float = 0.90
    CONTEXT_COMPRESSION_MIN_SENTENCE_CHARS: int = 20

    # Ingestion
    STORAGE_BACKEND: str = Field(default="local", description="local | supabase | s3")
    UPLOAD_DIR: str = "./data/uploads"
    TEMP_UPLOAD_DIR: str = "./tmp/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list[str] = ["pdf", "docx", "txt"]

    # Supabase Storage (used when STORAGE_BACKEND=supabase)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "legal-documents"
    SUPABASE_STORAGE_PATH_PREFIX: str = "uploads"

    # S3-compatible object storage (used when STORAGE_BACKEND=s3; works with AWS S3 / Cloudflare R2)
    S3_ENDPOINT_URL: str = ""
    S3_BUCKET: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_REGION: str = "auto"
    S3_PATH_PREFIX: str = "uploads"

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
    LANGFUSE_BASE_URL: str = ""

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
        self.DATABASE_URL = _strip_env_url(self.DATABASE_URL)
        self.DATABASE_SYNC_URL = _strip_env_url(self.DATABASE_SYNC_URL)

        if self.DATABASE_URL:
            normalized = _with_postgres_driver(self.DATABASE_URL, "asyncpg")
            if normalized != self.DATABASE_URL:
                self.DATABASE_URL = normalized
        else:
            self.DATABASE_URL = _build_postgres_url(
                driver="asyncpg",
                user=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                database=self.POSTGRES_DB,
            )

        if self.DATABASE_SYNC_URL:
            normalized = _with_postgres_driver(self.DATABASE_SYNC_URL, "psycopg2")
            if normalized != self.DATABASE_SYNC_URL:
                self.DATABASE_SYNC_URL = normalized
        elif self.DATABASE_URL:
            self.DATABASE_SYNC_URL = _with_postgres_driver(self.DATABASE_URL, "psycopg2")
        else:
            self.DATABASE_SYNC_URL = _build_postgres_url(
                driver="psycopg2",
                user=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                database=self.POSTGRES_DB,
            )

        if self.DATABASE_URL and self.DATABASE_SYNC_URL:
            from sqlalchemy.engine import make_url

            runtime = make_url(self.DATABASE_URL)
            sync = make_url(self.DATABASE_SYNC_URL)
            if runtime.username != sync.username:
                raise ValueError(
                    "DATABASE_URL and DATABASE_SYNC_URL use different usernames. "
                    "Copy both fresh Neon connection strings after a password reset."
                )
            if runtime.password != sync.password:
                raise ValueError(
                    "DATABASE_URL and DATABASE_SYNC_URL use different passwords. "
                    "After a Neon password reset, update both variables from the Neon dashboard."
                )

        return self

    @model_validator(mode="after")
    def _validate_vector_settings(self) -> Self:
        backend = self.VECTOR_BACKEND.strip().lower()
        if backend not in {"pgvector", "qdrant"}:
            raise ValueError("VECTOR_BACKEND must be either 'pgvector' or 'qdrant'.")

        if backend != self.VECTOR_BACKEND:
            self.VECTOR_BACKEND = backend

        if backend == "qdrant":
            missing = [
                key
                for key, value in {
                    "QDRANT_URL": self.QDRANT_URL,
                    "QDRANT_COLLECTION_NAME": self.QDRANT_COLLECTION_NAME,
                }.items()
                if not value.strip()
            ]
            if missing:
                raise ValueError(
                    "Qdrant configuration incomplete: set " + ", ".join(missing)
                )

        return self

    @model_validator(mode="after")
    def _validate_storage_settings(self) -> Self:
        backend = self.STORAGE_BACKEND.strip().lower()
        if backend not in {"local", "supabase", "s3"}:
            raise ValueError("STORAGE_BACKEND must be 'local', 'supabase', or 's3'.")

        if backend != self.STORAGE_BACKEND:
            self.STORAGE_BACKEND = backend

        if backend == "supabase":
            missing = [
                key
                for key, value in {
                    "SUPABASE_URL": self.SUPABASE_URL,
                    "SUPABASE_SERVICE_ROLE_KEY": self.SUPABASE_SERVICE_ROLE_KEY,
                    "SUPABASE_STORAGE_BUCKET": self.SUPABASE_STORAGE_BUCKET,
                }.items()
                if not value.strip()
            ]
            if missing:
                raise ValueError(
                    "Supabase storage configuration incomplete: set " + ", ".join(missing)
                )
        elif backend == "s3":
            missing = [
                key
                for key, value in {
                    "S3_BUCKET": self.S3_BUCKET,
                    "S3_ACCESS_KEY_ID": self.S3_ACCESS_KEY_ID,
                    "S3_SECRET_ACCESS_KEY": self.S3_SECRET_ACCESS_KEY,
                }.items()
                if not value.strip()
            ]
            if missing:
                raise ValueError(
                    "S3 storage configuration incomplete: set " + ", ".join(missing)
                )

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

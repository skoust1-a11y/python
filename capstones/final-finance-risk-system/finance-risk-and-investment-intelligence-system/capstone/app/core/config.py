from __future__ import annotations

from functools import lru_cache
from typing import List, Tuple

from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    log_dir: str = "logs"
    version: str = "0.4.0"

    auth_mode: str = "jwt"
    jwt_secret: str = "change-me-in-local-only"
    jwt_algorithm: str = "HS256"
    session_ttl_minutes: int = 60
    seed_password: str = "Password123"

    auth_database_url: str = "postgresql+psycopg://skoust@localhost:5432/finance_auth_db"
    database_url: str = "postgresql+psycopg://skoust@localhost:5432/finance_risk_db"
    stock_database_url: str = "postgresql+psycopg://skoust@localhost:5432/finance_stock_db"

    llm_provider: str = "openai"
    llm_fallback_provider: str = ""
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model_router: str = ""
    llm_model_agent: str = ""
    llm_temperature: float = 0.0
    llm_timeout_s: int = 20
    llm_max_retries: int = 2
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model_router: str = "gpt-4o-mini"
    openai_model_agent: str = "gpt-4o"
    xai_api_key: str = ""
    xai_base_url: str = "https://api.x.ai/v1"
    xai_model_router: str = "grok-4-fast"
    xai_model_agent: str = "grok-4"
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    gemini_model_router: str = "gemini-3.8-flash"
    gemini_model_agent: str = "gemini-3.8-flash"
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model_router: str = "openai/gpt-oss-120b"
    groq_model_agent: str = "openai/gpt-oss-20b"
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    ollama_model: str = "llama3.2"
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 1536

    retrieval_top_k: int = 5
    retrieval_top_k_max: int = 10
    retrieval_min_score: float = 0.35
    retrieval_weak_score: float = 0.2
    retrieval_vector_weight: float = 0.4
    retrieval_lexical_weight: float = 0.6
    retrieval_rrf_k: int = 60
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 180
    chunk_min_chars: int = 40
    citation_excerpt_chars: int = 280

    risk_score_medium: int = 30
    risk_score_high: int = 70
    risk_score_escalation: int = 80
    confidence_escalation_floor: float = 0.60
    stale_high_risk_days: int = 180
    sector_allocation_cap: float = 25.0
    emerging_market_cap: float = 15.0
    default_holdings_limit: int = 5
    default_min_allocation: float = 10.0
    max_sql_rows: int = 100

    corpus_local_path: str = "Documents"
    current_factors_enabled: bool = True
    market_max_stale_seconds: int = 900
    market_http_timeout_s: float = 8.0
    yahoo_chart_url: str = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    yahoo_search_url: str = "https://query1.finance.yahoo.com/v1/finance/search"
    news_max_age_hours: int = 48
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    render_external_url: str = ""
    rate_limit_per_minute: int = 30
    rate_window_seconds: int = 60
    max_tokens_per_request: int = 8000
    daily_budget_usd: float = 5.0
    cost_tracking_enabled: bool = True

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"

    @field_validator("auth_mode")
    @classmethod
    def _auth_mode(cls, value: str) -> str:
        if value not in ("stub", "jwt"):
            raise ValueError("AUTH_MODE must be stub or jwt")
        return value

    @field_validator("llm_provider", "llm_fallback_provider")
    @classmethod
    def _llm_provider(cls, value: str, info: ValidationInfo) -> str:
        aliases = {"xai": "grok", "google": "gemini", "llama": "ollama", "local": "ollama"}
        name = aliases.get(value.strip().lower(), value.strip().lower())
        if not name and info.field_name == "llm_fallback_provider":
            return ""
        if name not in ("openai", "grok", "gemini", "groq", "ollama"):
            raise ValueError("{} must be openai, grok, gemini, groq, or ollama".format(info.field_name.upper()))
        return name

    def cors_origin_list(self) -> List[str]:
        origins = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        extra = self.render_external_url.rstrip("/")
        if extra and extra not in origins:
            origins.append(extra)
        return origins

    def llm_catalog(self, provider: str = "") -> Tuple[str, str, str]:
        catalog = {
            "openai": (self.openai_base_url, self.openai_model_router, self.openai_model_agent),
            "grok": (self.xai_base_url, self.xai_model_router, self.xai_model_agent),
            "gemini": (self.gemini_base_url, self.gemini_model_router, self.gemini_model_agent),
            "groq": (self.groq_base_url, self.groq_model_router, self.groq_model_agent),
        }
        return catalog[provider or self.llm_provider]

    def validate_runtime(self) -> None:
        if self.app_env == "prod":
            if self.auth_mode == "stub":
                raise RuntimeError("AUTH_MODE=stub is forbidden when APP_ENV=prod")
            if self.jwt_secret in ("", "change-me-in-local-only", "REPLACE_ME"):
                raise RuntimeError("JWT_SECRET must be set for production")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime()
    return settings

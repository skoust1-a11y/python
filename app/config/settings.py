"""Environment-driven application settings.

Provider names and credentials live here so business logic never hardcodes vendors.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration sourced from environment variables and optional `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    app_name: str = Field(default="Autonomous Investment Strategy Board")
    app_env: str = Field(default="development")
    app_host: str = Field(default="127.0.0.1")
    app_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")

    llm_provider: str = Field(default="stub")
    fallback_llm_provider: str = Field(default="")
    llm_timeout_seconds: float = Field(default=30.0, gt=0)

    openai_llm_model: str = Field(default="gpt-4o-mini")
    openai_llm_api_key: str = Field(default="")
    openai_llm_base_url: str = Field(default="")

    groq_llm_model: str = Field(default="llama-3.3-70b-versatile")
    groq_llm_api_key: str = Field(default="")

    azure_llm_model: str = Field(default="")
    azure_llm_api_key: str = Field(default="")
    azure_llm_endpoint: str = Field(default="")
    azure_llm_api_version: str = Field(default="2024-10-21")
    azure_llm_deployment: str = Field(default="")

    google_llm_model: str = Field(default="gemini-2.0-flash")
    google_llm_api_key: str = Field(default="")

    market_data_provider: str = Field(default="stub")
    market_data_api_key: str = Field(default="")
    market_data_base_url: str = Field(default="")

    fundamental_data_provider: str = Field(default="stub")
    fundamental_data_api_key: str = Field(default="")
    fundamental_data_base_url: str = Field(default="")

    news_provider: str = Field(default="stub")
    news_api_key: str = Field(default="")
    news_base_url: str = Field(default="")

    portfolio_max_upload_bytes: int = Field(default=2_097_152, gt=0)
    portfolio_upload_ttl_seconds: int = Field(default=3600, gt=0)

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local"}

    def selected_providers(self) -> dict[str, str]:
        """Return configured adapter names without exposing secrets."""
        selected = {
            "llm": self.llm_provider,
            "market_data": self.market_data_provider,
            "fundamental_data": self.fundamental_data_provider,
            "news": self.news_provider,
        }
        fallback = self.fallback_llm_provider.strip()
        if fallback:
            selected["llm_fallback"] = fallback
        return selected


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings() -> None:
    """Clear the cached settings instance. Intended for tests."""
    get_settings.cache_clear()

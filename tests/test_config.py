from app.config.logging import configure_logging
from app.config.settings import Settings, get_settings, reset_settings
from tests.helpers import make_settings


def test_default_settings_use_stub_providers() -> None:
    settings = make_settings()
    assert settings.selected_providers() == {
        "llm": "stub",
        "market_data": "stub",
        "fundamental_data": "stub",
        "news": "stub",
    }


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("APP_PORT", "9000")
    settings = Settings(_env_file=None)
    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"
    assert settings.llm_provider == "stub"
    assert settings.app_port == 9000


def test_settings_load_data_providers_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "stub")
    monkeypatch.setenv("FUNDAMENTAL_DATA_PROVIDER", "stub")
    monkeypatch.setenv("NEWS_PROVIDER", "stub")
    monkeypatch.setenv("MARKET_DATA_API_KEY", "market-secret")
    monkeypatch.setenv("FUNDAMENTAL_DATA_API_KEY", "fundamentals-secret")
    monkeypatch.setenv("NEWS_API_KEY", "news-secret")
    settings = Settings(_env_file=None)
    assert settings.market_data_provider == "stub"
    assert settings.fundamental_data_provider == "stub"
    assert settings.news_provider == "stub"
    selected = settings.selected_providers()
    assert selected["market_data"] == "stub"
    assert selected["fundamental_data"] == "stub"
    assert selected["news"] == "stub"
    serialized = str(selected)
    assert "market-secret" not in serialized
    assert "fundamentals-secret" not in serialized
    assert "news-secret" not in serialized


def test_settings_load_llm_provider_and_models_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("FALLBACK_LLM_PROVIDER", "openai")
    monkeypatch.setenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("GROQ_LLM_API_KEY", "gsk-test")
    monkeypatch.setenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("GOOGLE_LLM_MODEL", "gemini-2.0-flash")
    monkeypatch.setenv("AZURE_LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "12.5")
    settings = Settings(_env_file=None)
    assert settings.llm_provider == "groq"
    assert settings.fallback_llm_provider == "openai"
    assert settings.groq_llm_model == "llama-3.3-70b-versatile"
    assert settings.openai_llm_model == "gpt-4o-mini"
    assert settings.google_llm_model == "gemini-2.0-flash"
    assert settings.azure_llm_model == "gpt-4o"
    assert settings.llm_timeout_seconds == 12.5
    assert settings.selected_providers()["llm"] == "groq"
    assert settings.selected_providers()["llm_fallback"] == "openai"
    # Secrets are loaded but never returned by selected_providers.
    assert "gsk-test" not in str(settings.selected_providers())
    assert "sk-test" not in str(settings.selected_providers())


def test_settings_load_portfolio_upload_limits(monkeypatch) -> None:
    monkeypatch.setenv("PORTFOLIO_MAX_UPLOAD_BYTES", "1024")
    monkeypatch.setenv("PORTFOLIO_UPLOAD_TTL_SECONDS", "60")
    settings = Settings(_env_file=None)
    assert settings.portfolio_max_upload_bytes == 1024
    assert settings.portfolio_upload_ttl_seconds == 60


def test_get_settings_cache_can_be_reset(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "first")
    reset_settings()
    assert get_settings().app_env == "first"
    monkeypatch.setenv("APP_ENV", "second")
    reset_settings()
    assert get_settings().app_env == "second"
    reset_settings()


def test_configure_logging_accepts_invalid_level() -> None:
    configure_logging(make_settings(log_level="not-a-level"))


def test_gitignore_excludes_env_file() -> None:
    from pathlib import Path

    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore
    assert ".env.example" in gitignore or "!.env.example" in gitignore

"""Shared helpers for LLM adapter construction."""

from app.exceptions import ConfigurationError


def require_configured(value: str, env_name: str) -> str:
    """Return a stripped setting or raise a configuration error. Never echoes secrets."""
    if value is None or not str(value).strip():
        raise ConfigurationError(f"{env_name} is required for the selected LLM provider.")
    return str(value).strip()

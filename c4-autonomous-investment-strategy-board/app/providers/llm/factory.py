"""Select and construct LLM adapters from environment configuration.

Adding a vendor means adding an adapter module and registering it here.
Agent and service code keeps depending on `LLMProvider`.
"""

from __future__ import annotations

import logging

from app.config.settings import Settings
from app.exceptions import ConfigurationError
from app.providers.contracts import LLMProvider
from app.providers.llm.azure import AzureLLMProvider
from app.providers.llm.fallback import FallbackLLMProvider
from app.providers.llm.google import GoogleLLMProvider
from app.providers.llm.groq import GroqLLMProvider
from app.providers.llm.openai import OpenAILLMProvider
from app.providers.llm.stub import StubLLMProvider

logger = logging.getLogger("app.providers.llm")

LLM_ADAPTERS: dict[str, type[LLMProvider]] = {
    "stub": StubLLMProvider,
    "openai": OpenAILLMProvider,
    "groq": GroqLLMProvider,
    "google": GoogleLLMProvider,
    "azure": AzureLLMProvider,
}

_PROVIDER_ALIASES = {
    "gemini": "google",
    "google_genai": "google",
    "azureopenai": "azure",
    "azure_openai": "azure",
}


def normalize_llm_provider(value: str) -> str:
    """Normalize provider names and aliases to a registry key."""
    key = value.strip().lower().replace("-", "_")
    return _PROVIDER_ALIASES.get(key, key)


def available_llm_providers() -> str:
    return ", ".join(sorted(LLM_ADAPTERS))


def build_llm_provider(settings: Settings) -> LLMProvider:
    """Instantiate the configured LLM, wrapping a fallback adapter when set."""
    primary = _create_llm(settings.llm_provider, settings, kind="LLM_PROVIDER")
    logger.info(
        "Instantiated LLM provider '%s' (model='%s', timeout=%ss)",
        primary.name,
        primary.model or "(none)",
        settings.llm_timeout_seconds,
    )

    fallback_configured = settings.fallback_llm_provider.strip()
    if not fallback_configured:
        return primary

    if normalize_llm_provider(fallback_configured) == normalize_llm_provider(settings.llm_provider):
        logger.info("FALLBACK_LLM_PROVIDER matches LLM_PROVIDER; fallback disabled.")
        return primary

    fallback = _create_llm(fallback_configured, settings, kind="FALLBACK_LLM_PROVIDER")
    logger.info(
        "Instantiated fallback LLM provider '%s' (model='%s')",
        fallback.name,
        fallback.model or "(none)",
    )
    return FallbackLLMProvider(primary, fallback)


def _create_llm(configured: str, settings: Settings, *, kind: str) -> LLMProvider:
    if not configured.strip():
        raise ConfigurationError(f"{kind} is required.")
    key = normalize_llm_provider(configured)
    adapter_cls = LLM_ADAPTERS.get(key)
    if adapter_cls is None:
        raise ConfigurationError(
            f"Unknown {kind} '{configured}'. Available adapters: {available_llm_providers()}."
        )
    return adapter_cls(settings)

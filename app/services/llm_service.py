"""LLM provider abstraction — OpenAI and Anthropic."""

from llama_index.llms.anthropic import Anthropic
from llama_index.llms.openai import OpenAI

from app.core.config import settings
from app.core.exceptions import LLMProviderError


class LLMService:
    """Factory and fallback routing for LLM providers."""

    def get_llm(self, provider: str | None = None, *, allow_fallback: bool = True):
        requested = provider or settings.DEFAULT_LLM_PROVIDER
        try:
            return self._create_llm(requested)
        except LLMProviderError:
            if not allow_fallback or requested == settings.FALLBACK_LLM_PROVIDER:
                raise
            return self._create_llm(settings.FALLBACK_LLM_PROVIDER)

    def _create_llm(self, provider: str):
        if provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise LLMProviderError("openai", "API key not configured")
            return OpenAI(model=settings.OPENAI_CHAT_MODEL, api_key=settings.OPENAI_API_KEY)

        if provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise LLMProviderError("anthropic", "API key not configured")
            return Anthropic(model=settings.ANTHROPIC_CHAT_MODEL, api_key=settings.ANTHROPIC_API_KEY)

        raise LLMProviderError(provider, "Unknown provider")

"""Groq Chat Completions adapter (OpenAI-compatible API)."""

from openai import OpenAI

from app.config.settings import Settings
from app.providers.llm.config import require_configured
from app.providers.llm.openai_compatible import OpenAICompatibleLLMProvider

GROQ_OPENAI_BASE_URL = "https://api.groq.com/openai/v1"


class GroqLLMProvider(OpenAICompatibleLLMProvider):
    def __init__(self, settings: Settings) -> None:
        api_key = require_configured(settings.groq_llm_api_key, "GROQ_LLM_API_KEY")
        model = require_configured(settings.groq_llm_model, "GROQ_LLM_MODEL")
        super().__init__(
            name="groq",
            model=model,
            client=OpenAI(
                api_key=api_key,
                base_url=GROQ_OPENAI_BASE_URL,
                timeout=settings.llm_timeout_seconds,
                max_retries=3,
            ),
            timeout_seconds=settings.llm_timeout_seconds,
            api_key=api_key,
        )

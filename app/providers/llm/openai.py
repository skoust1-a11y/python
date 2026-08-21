"""OpenAI Chat Completions adapter."""

from openai import OpenAI

from app.config.settings import Settings
from app.providers.llm.config import require_configured
from app.providers.llm.openai_compatible import OpenAICompatibleLLMProvider


class OpenAILLMProvider(OpenAICompatibleLLMProvider):
    def __init__(self, settings: Settings) -> None:
        api_key = require_configured(settings.openai_llm_api_key, "OPENAI_LLM_API_KEY")
        model = require_configured(settings.openai_llm_model, "OPENAI_LLM_MODEL")
        client_kwargs: dict[str, object] = {
            "api_key": api_key,
            "timeout": settings.llm_timeout_seconds,
            "max_retries": 0,
        }
        if settings.openai_llm_base_url.strip():
            client_kwargs["base_url"] = settings.openai_llm_base_url.strip()
        super().__init__(
            name="openai",
            model=model,
            client=OpenAI(**client_kwargs),
            timeout_seconds=settings.llm_timeout_seconds,
            api_key=api_key,
        )

"""Azure OpenAI Chat Completions adapter."""

from openai import AzureOpenAI

from app.config.settings import Settings
from app.providers.llm.config import require_configured
from app.providers.llm.openai_compatible import OpenAICompatibleLLMProvider


class AzureLLMProvider(OpenAICompatibleLLMProvider):
    def __init__(self, settings: Settings) -> None:
        api_key = require_configured(settings.azure_llm_api_key, "AZURE_LLM_API_KEY")
        model = require_configured(settings.azure_llm_model, "AZURE_LLM_MODEL")
        endpoint = require_configured(settings.azure_llm_endpoint, "AZURE_LLM_ENDPOINT")
        api_version = require_configured(settings.azure_llm_api_version, "AZURE_LLM_API_VERSION")
        deployment = settings.azure_llm_deployment.strip() or model
        super().__init__(
            name="azure",
            model=deployment,
            client=AzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version=api_version,
                timeout=settings.llm_timeout_seconds,
                max_retries=0,
            ),
            timeout_seconds=settings.llm_timeout_seconds,
            api_key=api_key,
        )

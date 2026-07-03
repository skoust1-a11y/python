"""LLM provider abstraction — OpenAI, Anthropic, Google, Groq, and Azure OpenAI."""

import logging
import time
import traceback

from llama_index.llms.anthropic import Anthropic
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.llms.groq import Groq
from llama_index.llms.openai import OpenAI

from app.core.config import settings
from app.core.exceptions import LLMProviderError
from app.utils.google_http import build_google_genai_http_options, build_httpx_clients

logger = logging.getLogger(__name__)

SUPPORTED_LLM_PROVIDERS = frozenset(
    {
        "openai",
        "anthropic",
        "google",
        "groq",
        "azureopenai",
    }
)


def normalize_llm_provider(provider: str) -> str:
    """Normalize provider aliases to canonical names."""
    normalized = provider.strip().lower().replace("-", "_")
    aliases = {
        "gemini": "google",
        "azure": "azureopenai",
        "azure_openai": "azureopenai",
    }
    return aliases.get(normalized, normalized)


def _key_status(value: str) -> str:
    return "YES" if value.strip() else "NO"


def _provider_model(provider: str) -> str:
    provider = normalize_llm_provider(provider)
    models = {
        "openai": settings.OPENAI_CHAT_MODEL,
        "anthropic": settings.ANTHROPIC_CHAT_MODEL,
        "google": settings.GEMINI_CHAT_MODEL,
        "groq": settings.GROQ_CHAT_MODEL,
        "azureopenai": settings.AZURE_OPENAI_CHAT_MODEL,
    }
    return models.get(provider, "unknown")


def _provider_api_key_status(provider: str) -> str:
    provider = normalize_llm_provider(provider)
    keys = {
        "openai": settings.OPENAI_API_KEY,
        "anthropic": settings.ANTHROPIC_API_KEY,
        "google": settings.GEMINI_API_KEY,
        "groq": settings.GROQ_API_KEY,
        "azureopenai": settings.AZURE_OPENAI_API_KEY,
    }
    return _key_status(keys.get(provider, ""))


def _log_provider_creation(provider: str) -> None:
    provider = normalize_llm_provider(provider)
    logger.info(
        "Creating provider: %s\nModel            : %s\nAPI Key Present  : %s",
        provider,
        _provider_model(provider),
        _provider_api_key_status(provider),
    )


def log_llm_configuration() -> None:
    """Log resolved LLM provider configuration at application startup."""
    logger.info(
        "========== LLM CONFIG ==========\n\n"
        "DEFAULT_LLM_PROVIDER = %s\n"
        "FALLBACK_PROVIDER    = %s\n\n"
        "GOOGLE MODEL         = %s\n"
        "GROQ MODEL           = %s\n"
        "OPENAI MODEL         = %s\n\n"
        "GOOGLE KEY           = %s\n"
        "GROQ KEY             = %s\n"
        "OPENAI KEY           = %s\n\n"
        "===============================\n",
        settings.DEFAULT_LLM_PROVIDER,
        settings.FALLBACK_LLM_PROVIDER,
        settings.GEMINI_CHAT_MODEL,
        settings.GROQ_CHAT_MODEL,
        settings.OPENAI_CHAT_MODEL,
        _key_status(settings.GEMINI_API_KEY),
        _key_status(settings.GROQ_API_KEY),
        _key_status(settings.OPENAI_API_KEY),
    )


class LLMService:
    """Factory and fallback routing for LLM providers."""

    def get_llm(self, provider: str | None = None, *, allow_fallback: bool = True):
        requested_raw = provider or settings.DEFAULT_LLM_PROVIDER
        requested = normalize_llm_provider(requested_raw)
        fallback = normalize_llm_provider(settings.FALLBACK_LLM_PROVIDER)

        logger.info(
            "========== LLM REQUEST ==========\n"
            "Requested Provider : %s\n"
            "Normalized Provider: %s\n"
            "Default Provider   : %s\n"
            "Fallback Provider  : %s\n"
            "Allow Fallback     : %s\n"
            "=================================",
            requested_raw,
            requested,
            settings.DEFAULT_LLM_PROVIDER,
            settings.FALLBACK_LLM_PROVIDER,
            allow_fallback,
        )

        try:
            return self._create_llm(requested)
        except LLMProviderError as exc:
            if not allow_fallback or requested == fallback:
                raise
            logger.warning(
                "Primary provider '%s' creation failed, falling back to '%s': %s",
                requested,
                fallback,
                exc.message,
            )
            return self._create_llm(fallback)

    def _create_llm(self, provider: str):
        provider = normalize_llm_provider(provider)

        if provider == "openai":
            _log_provider_creation(provider)
            if not settings.OPENAI_API_KEY:
                raise LLMProviderError("openai", "API key not configured")
            return OpenAI(
                model=settings.OPENAI_CHAT_MODEL,
                api_key=settings.OPENAI_API_KEY,
                **build_httpx_clients(),
            )

        if provider == "anthropic":
            _log_provider_creation(provider)
            if not settings.ANTHROPIC_API_KEY:
                raise LLMProviderError("anthropic", "API key not configured")
            return Anthropic(model=settings.ANTHROPIC_CHAT_MODEL, api_key=settings.ANTHROPIC_API_KEY)

        if provider == "google":
            _log_provider_creation(provider)
            if not settings.GEMINI_API_KEY:
                raise LLMProviderError("google", "GEMINI_API_KEY not configured")
            return GoogleGenAI(
                model=settings.GEMINI_CHAT_MODEL,
                api_key=settings.GEMINI_API_KEY,
                http_options=build_google_genai_http_options(),
            )

        if provider == "groq":
            _log_provider_creation(provider)
            if not settings.GROQ_API_KEY:
                raise LLMProviderError("groq", "GROQ_API_KEY not configured")
            return Groq(
                model=settings.GROQ_CHAT_MODEL,
                api_key=settings.GROQ_API_KEY,
                **build_httpx_clients(),
            )

        if provider == "azureopenai":
            _log_provider_creation(provider)
            if not settings.AZURE_OPENAI_API_KEY:
                raise LLMProviderError("azureopenai", "AZURE_OPENAI_API_KEY not configured")
            if not settings.AZURE_OPENAI_ENDPOINT:
                raise LLMProviderError("azureopenai", "AZURE_OPENAI_ENDPOINT not configured")
            if not settings.AZURE_OPENAI_DEPLOYMENT:
                raise LLMProviderError("azureopenai", "AZURE_OPENAI_DEPLOYMENT not configured")
            return AzureOpenAI(
                engine=settings.AZURE_OPENAI_DEPLOYMENT,
                model=settings.AZURE_OPENAI_CHAT_MODEL,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
            )

    async def achat_with_fallback(
        self,
        messages,
        provider: str | None = None,
    ) -> tuple[str, str]:
        """Run chat completion, trying fallback providers on transient failures."""
        primary = normalize_llm_provider(provider or settings.DEFAULT_LLM_PROVIDER)
        fallback = normalize_llm_provider(settings.FALLBACK_LLM_PROVIDER)
        providers: list[str] = []
        provider_sources: dict[str, str] = {}
        for candidate, source in (
            (primary, "primary"),
            (fallback, "configured fallback"),
            ("openai", "hardcoded emergency fallback"),
            ("groq", "hardcoded emergency fallback"),
        ):
            normalized = normalize_llm_provider(candidate)
            if normalized not in providers:
                providers.append(normalized)
                provider_sources[normalized] = source

        provider_lines = "\n".join(
            f"{index}. {name} ({provider_sources[name]})"
            for index, name in enumerate(providers, start=1)
        )
        logger.info(
            "========== CHAT REQUEST ==========\n"
            "Primary Provider : %s\n"
            "Fallback Provider: %s\n\n"
            "Providers to Try:\n\n"
            "%s\n"
            "==================================",
            primary,
            fallback,
            provider_lines,
        )

        last_error: Exception | None = None
        attempt_results: dict[str, str] = {}
        final_provider: str | None = None

        for candidate in providers:
            logger.info("Trying provider: %s", candidate)
            start = time.perf_counter()
            try:
                llm = self.get_llm(candidate, allow_fallback=False)
                model = getattr(llm, "model", None) or _provider_model(candidate)
                message_count = len(messages)
                logger.info(
                    "Calling provider: %s\nModel           : %s\nMessage Count   : %d",
                    candidate,
                    model,
                    message_count,
                )
                response = await llm.achat(messages)
                elapsed_ms = (time.perf_counter() - start) * 1000
                content = (response.message.content or "").strip()
                logger.info(
                    "SUCCESS\n\n"
                    "Provider : %s\n"
                    "Latency  : %.0f ms\n"
                    "Response Length : %d chars\n\n"
                    "Completed in %.0f ms",
                    candidate,
                    elapsed_ms,
                    len(content),
                    elapsed_ms,
                )
                attempt_results[candidate] = "SUCCESS"
                final_provider = candidate
                return content, candidate
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start) * 1000
                last_error = exc
                attempt_results[candidate] = "FAILED"
                logger.error(
                    "FAILED\n\n"
                    "Provider : %s\n"
                    "Exception: %s\n"
                    "Message  : %s\n\n"
                    "Traceback:\n%s\n\n"
                    "Failed after %.0f ms",
                    candidate,
                    type(exc).__name__,
                    exc,
                    traceback.format_exc(),
                    elapsed_ms,
                )
                logger.exception(
                    "Provider '%s' chat request failed after %.0f ms",
                    candidate,
                    elapsed_ms,
                )
                continue

        summary_lines = "\n".join(
            f"{name:<6} -> {attempt_results.get(name, 'SKIPPED')}" for name in providers
        )
        logger.error(
            "========== SUMMARY ==========\n\n"
            "%s\n\n"
            "Final Provider : %s\n\n"
            "=============================",
            summary_lines,
            final_provider,
        )

        raise LLMProviderError(primary, str(last_error or "all providers failed"))

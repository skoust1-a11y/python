"""Placeholder LLM adapter. Does not call a vendor API."""

from typing import Any

from app.config.settings import Settings
from app.exceptions import ProviderNotImplementedError
from app.providers.contracts import LLMProvider, TModel


class StubLLMProvider(LLMProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        return "stub"

    @property
    def model(self) -> str:
        return ""

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        raise ProviderNotImplementedError(
            "LLM adapter is not implemented for LLM_PROVIDER=stub. "
            "Set LLM_PROVIDER to openai, groq, google, or azure."
        )

    def complete_structured(
        self,
        prompt: str,
        response_model: type[TModel],
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TModel:
        raise ProviderNotImplementedError(
            "Structured LLM output is not implemented for LLM_PROVIDER=stub. "
            "Set LLM_PROVIDER to openai, groq, google, or azure."
        )

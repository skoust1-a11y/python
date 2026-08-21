"""Runtime fallback: if the primary LLM fails, retry once on the fallback adapter."""

from __future__ import annotations

import logging
from typing import Any

from app.exceptions import ProviderError
from app.providers.contracts import LLMProvider, TModel

logger = logging.getLogger("app.providers.llm")


class FallbackLLMProvider(LLMProvider):
    """Delegate to a primary adapter, then a configured fallback on provider errors."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider) -> None:
        self._primary = primary
        self._fallback = fallback

    @property
    def name(self) -> str:
        return self._primary.name

    @property
    def model(self) -> str:
        return self._primary.model

    @property
    def fallback_name(self) -> str | None:
        return self._fallback.name

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        try:
            return self._primary.complete(prompt, system=system, metadata=metadata)
        except ProviderError as exc:
            return self._retry(
                "complete",
                exc,
                lambda: self._fallback.complete(prompt, system=system, metadata=metadata),
            )

    def complete_structured(
        self,
        prompt: str,
        response_model: type[TModel],
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TModel:
        try:
            return self._primary.complete_structured(
                prompt,
                response_model,
                system=system,
                metadata=metadata,
            )
        except ProviderError as exc:
            return self._retry(
                "complete_structured",
                exc,
                lambda: self._fallback.complete_structured(
                    prompt,
                    response_model,
                    system=system,
                    metadata=metadata,
                ),
            )

    def _retry(self, operation: str, error: ProviderError, call):
        logger.warning(
            "Primary LLM provider '%s' failed during %s; trying fallback '%s'. Error: %s",
            self._primary.name,
            operation,
            self._fallback.name,
            error.message,
        )
        return call()

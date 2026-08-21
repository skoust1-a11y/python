"""Google Gemini adapter. Isolated from OpenAI-compatible providers."""

from __future__ import annotations

import json
from typing import Any

from google import genai
from google.genai import types

from app.config.settings import Settings
from app.exceptions import ProviderError
from app.providers.contracts import LLMProvider, TModel
from app.providers.llm.config import require_configured
from app.providers.llm.errors import to_provider_error
from app.providers.llm.parsing import STRUCTURED_OUTPUT_INSTRUCTION, parse_structured_output


class GoogleLLMProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        api_key = require_configured(settings.google_llm_api_key, "GOOGLE_LLM_API_KEY")
        self._model = require_configured(settings.google_llm_model, "GOOGLE_LLM_MODEL")
        self._api_key = api_key
        timeout_ms = max(1, int(settings.llm_timeout_seconds * 1000))
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout_ms),
        )

    @property
    def name(self) -> str:
        return "google"

    @property
    def model(self) -> str:
        return self._model

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        del metadata
        config: dict[str, Any] = {"temperature": 0}
        if system:
            config["system_instruction"] = system
        text = self._generate(prompt, config)
        if not text.strip():
            raise ProviderError("LLM returned an empty response.")
        return text

    def complete_structured(
        self,
        prompt: str,
        response_model: type[TModel],
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TModel:
        del metadata
        instruction = (
            f"{system}\n\n{STRUCTURED_OUTPUT_INSTRUCTION}" if system else STRUCTURED_OUTPUT_INSTRUCTION
        )
        config: dict[str, Any] = {
            "temperature": 0,
            "system_instruction": instruction,
            "response_mime_type": "application/json",
            "response_schema": response_model,
        }
        try:
            text = self._generate(prompt, config)
            return parse_structured_output(text, response_model)
        except ProviderError as exc:
            if "timed out" in exc.message.lower():
                raise
            schema_prompt = (
                f"{prompt}\n\nJSON schema:\n{json.dumps(response_model.model_json_schema())}"
            )
            fallback_config: dict[str, Any] = {
                "temperature": 0,
                "system_instruction": instruction,
                "response_mime_type": "application/json",
            }
            text = self._generate(schema_prompt, fallback_config)
            return parse_structured_output(text, response_model)

    def _generate(self, prompt: str, config: dict[str, Any]) -> str:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            raise to_provider_error(exc, extra_secrets=[self._api_key]) from exc
        text = getattr(response, "text", None)
        return "" if text is None else str(text)

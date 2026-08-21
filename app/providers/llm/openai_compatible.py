"""OpenAI-compatible chat completions used by OpenAI, Groq, and Azure adapters."""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from app.exceptions import ProviderError
from app.providers.contracts import LLMProvider, TModel
from app.providers.llm.errors import to_provider_error
from app.providers.llm.parsing import STRUCTURED_OUTPUT_INSTRUCTION, parse_structured_output

logger = logging.getLogger("app.providers.llm")


class _Completions(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class _Chat(Protocol):
    completions: _Completions


class OpenAICompatibleClient(Protocol):
    chat: _Chat


class OpenAICompatibleLLMProvider(LLMProvider):
    """Text and JSON completions over an OpenAI-style Chat Completions API."""

    def __init__(
        self,
        *,
        name: str,
        model: str,
        client: OpenAICompatibleClient,
        timeout_seconds: float,
        api_key: str,
    ) -> None:
        self._name = name
        self._model = model
        self._client = client
        self._timeout_seconds = timeout_seconds
        self._api_key = api_key

    @property
    def name(self) -> str:
        return self._name

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
        return self._chat(self._messages(prompt, system), json_mode=False)

    def complete_structured(
        self,
        prompt: str,
        response_model: type[TModel],
        *,
        system: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TModel:
        del metadata
        schema = json.dumps(response_model.model_json_schema())
        user_prompt = f"{prompt}\n\nJSON schema:\n{schema}"
        instruction = (
            f"{system}\n\n{STRUCTURED_OUTPUT_INSTRUCTION}" if system else STRUCTURED_OUTPUT_INSTRUCTION
        )
        text = self._chat(self._messages(user_prompt, instruction), json_mode=True)
        return parse_structured_output(text, response_model)

    def _messages(self, prompt: str, system: str | None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _chat(self, messages: list[dict[str, str]], *, json_mode: bool) -> str:
        logger.debug(
            "Dispatching LLM completion provider=%s model=%s json_mode=%s messages=%d",
            self._name,
            self._model,
            json_mode,
            len(messages),
        )
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": 0,
            "timeout": self._timeout_seconds,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise to_provider_error(exc, extra_secrets=[self._api_key]) from exc
        text = _message_content(response)
        if not text.strip():
            raise ProviderError("LLM returned an empty response.")
        return text


def _message_content(response: Any) -> str:
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise ProviderError("LLM returned an unexpected response payload.") from exc
    if content is None:
        return ""
    return str(content)

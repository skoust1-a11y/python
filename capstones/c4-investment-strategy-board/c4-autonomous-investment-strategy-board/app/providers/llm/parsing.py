"""Parse LLM text into Pydantic models without depending on a vendor SDK."""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.exceptions import ProviderError

TModel = TypeVar("TModel", bound=BaseModel)

_LEADING_FENCE = re.compile(r"^```(?:json)?\s*", re.IGNORECASE)
_TRAILING_FENCE = re.compile(r"\s*```$")
_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)

STRUCTURED_OUTPUT_INSTRUCTION = (
    "You are a structured-output generator. "
    "Respond with a single JSON object that matches the given schema. "
    "Do not include markdown fences or commentary."
)


def parse_structured_output(text: str, response_model: type[TModel]) -> TModel:
    """Validate JSON text as `response_model`, accepting optional markdown fences."""
    if not text or not str(text).strip():
        raise ProviderError("LLM returned an empty structured response.")

    candidate = str(text).strip()
    if candidate.startswith("```"):
        candidate = _LEADING_FENCE.sub("", candidate)
        candidate = _TRAILING_FENCE.sub("", candidate)
        candidate = candidate.strip()

    last_error: Exception | None = None
    for payload in _candidate_payloads(candidate):
        try:
            return response_model.model_validate_json(payload)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc

    raise ProviderError("LLM structured output did not match the expected schema.") from last_error


def _candidate_payloads(candidate: str) -> list[str]:
    payloads = [candidate]
    match = _JSON_OBJECT.search(candidate)
    if match:
        payloads.append(match.group(0))
    return payloads

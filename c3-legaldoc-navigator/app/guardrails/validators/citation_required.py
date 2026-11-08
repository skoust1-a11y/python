"""Require source citations for substantive legal findings."""

from __future__ import annotations

import re
from typing import Callable, Dict, Optional

from guardrails.validators import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)

from app.guardrails.constants import CITATION_PATTERNS, INSUFFICIENT_INFO_PHRASES

_CITATION_RE = re.compile("|".join(f"(?:{p})" for p in CITATION_PATTERNS), re.IGNORECASE)

# Indicators that the response makes substantive factual claims.
_CLAIM_INDICATORS = re.compile(
    r"\b(?:states?|provides?|requires?|obligat(?:es?|ion)|shall|party|parties|"
    r"agreement|contract|clause|section|liability|damages|term(?:ination)?|"
    r"effective date|governing law)\b",
    re.IGNORECASE,
)


def _is_insufficient_info_response(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in INSUFFICIENT_INFO_PHRASES)


@register_validator(name="legal/citation-required", data_type="string")
class CitationRequiredValidator(Validator):
    """Require citations when the response contains substantive legal content."""

    def __init__(
        self,
        min_length: int = 80,
        on_fail: Optional[Callable] = None,
    ) -> None:
        super().__init__(on_fail=on_fail, min_length=min_length)
        self.min_length = min_length

    def _validate(self, value: str, metadata: Dict) -> ValidationResult:
        if _is_insufficient_info_response(value):
            return PassResult()

        sources = metadata.get("sources") or []
        if not sources:
            return PassResult()

        is_strict = metadata.get("response_mode") == "strict"
        is_substantive = len(value.strip()) >= self.min_length or bool(
            _CLAIM_INDICATORS.search(value)
        )
        if not is_substantive and not is_strict:
            return PassResult()

        if _CITATION_RE.search(value):
            return PassResult()

        if is_strict:
            return FailResult(
                error_message=(
                    "STRICT mode requires a [Source N] citation for every factual "
                    "statement drawn from the retrieved documents."
                ),
            )

        return FailResult(
            error_message=(
                "Substantive legal content must include citations "
                "(e.g. [Source 1], Section, or Clause references)."
            ),
        )

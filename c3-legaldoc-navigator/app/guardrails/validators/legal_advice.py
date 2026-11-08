"""Detect prescriptive legal advice and recommendations without evidence."""

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

from app.guardrails.constants import CITATION_PATTERNS, LEGAL_ADVICE_PATTERNS

_ADVICE_RE = re.compile("|".join(f"(?:{p})" for p in LEGAL_ADVICE_PATTERNS), re.IGNORECASE)
_CITATION_RE = re.compile("|".join(f"(?:{p})" for p in CITATION_PATTERNS), re.IGNORECASE)


@register_validator(name="legal/advice-detector", data_type="string")
class LegalAdviceDetector(Validator):
    """Block prescriptive legal advice and recommendations lacking source evidence."""

    def __init__(self, on_fail: Optional[Callable] = None) -> None:
        super().__init__(on_fail=on_fail)

    def _validate(self, value: str, metadata: Dict) -> ValidationResult:
        if not _ADVICE_RE.search(value):
            return PassResult()

        sources = metadata.get("sources") or []
        if not sources:
            return FailResult(
                error_message=(
                    "Response contains legal advice or recommendations but no "
                    "retrieved sources were available to support them."
                ),
            )

        if not _CITATION_RE.search(value):
            return FailResult(
                error_message=(
                    "Response contains legal advice or recommendations without "
                    "citations to supporting source material."
                ),
            )

        return PassResult()

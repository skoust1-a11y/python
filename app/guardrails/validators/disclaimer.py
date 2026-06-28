"""Ensure every response includes the mandatory legal disclaimer."""

from __future__ import annotations

from typing import Callable, Dict, Optional

from guardrails.validators import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)

from app.guardrails.constants import DISCLAIMER_FOOTER, LEGAL_DISCLAIMER


@register_validator(name="legal/disclaimer", data_type="string")
class DisclaimerValidator(Validator):
    """Append the required legal disclaimer when it is missing."""

    def __init__(self, on_fail: Optional[Callable] = None) -> None:
        super().__init__(on_fail=on_fail)

    def _validate(self, value: str, metadata: Dict) -> ValidationResult:
        if LEGAL_DISCLAIMER in value:
            return PassResult()

        fixed = value.rstrip() + DISCLAIMER_FOOTER
        return FailResult(
            error_message="Response is missing the required legal disclaimer.",
            fix_value=fixed,
        )

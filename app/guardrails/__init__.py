"""Input/output guardrails for legal document AI safety."""

from app.guardrails.fallbacks import get_fallback_response
from app.guardrails.guard import create_legal_guard
from app.guardrails.validator import GuardrailValidationResult, GuardrailValidator

__all__ = [
    "GuardrailValidationResult",
    "GuardrailValidator",
    "create_legal_guard",
    "get_fallback_response",
]

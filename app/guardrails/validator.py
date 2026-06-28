"""Pre-query and post-response validation guardrails using Guardrails AI."""

from __future__ import annotations

from dataclasses import dataclass, field

from guardrails import Guard

from app.core.config import settings
from app.core.exceptions import GuardrailViolationError
from app.guardrails.constants import DISCLAIMER_FOOTER, LEGAL_DISCLAIMER
from app.guardrails.fallbacks import get_fallback_response
from app.guardrails.guard import BLOCKING_VALIDATOR_NAMES, create_legal_guard


@dataclass
class GuardrailValidationResult:
    """Outcome of post-response guardrail validation."""

    answer: str
    passed: bool
    used_fallback: bool = False
    violations: list[str] = field(default_factory=list)


class GuardrailValidator:
    """Enforce safety constraints on user queries and LLM responses."""

    BLOCKED_PATTERNS = [
        "ignore previous instructions",
        "disregard all rules",
    ]

    def __init__(self, guard: Guard | None = None) -> None:
        self._guard = guard or create_legal_guard()

    def validate_query(self, query: str) -> None:
        if not settings.ENABLE_GUARDRAILS:
            return

        if len(query) > settings.MAX_QUERY_LENGTH:
            raise GuardrailViolationError(
                f"Query exceeds maximum length of {settings.MAX_QUERY_LENGTH} characters."
            )

        lowered = query.lower()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in lowered:
                raise GuardrailViolationError("Query contains blocked content.")

    def validate_response(
        self,
        response: str,
        *,
        sources: list[dict] | None = None,
        question: str | None = None,
    ) -> str:
        """Validate and optionally replace an LLM response."""
        result = self.validate_response_detailed(
            response,
            sources=sources,
            question=question,
        )
        return result.answer

    def validate_response_detailed(
        self,
        response: str,
        *,
        sources: list[dict] | None = None,
        question: str | None = None,
    ) -> GuardrailValidationResult:
        """Validate an LLM response and return structured guardrail metadata."""
        source_list = sources or []

        if not settings.ENABLE_GUARDRAILS:
            return GuardrailValidationResult(
                answer=self._ensure_disclaimer(response),
                passed=True,
            )

        metadata = {
            "sources": source_list,
            "question": question or "",
        }

        outcome = self._guard.validate(response, metadata=metadata)

        blocking_failures = [
            summary.validator_name
            for summary in (outcome.validation_summaries or [])
            if summary.validator_status == "fail"
            and summary.validator_name in BLOCKING_VALIDATOR_NAMES
        ]

        if blocking_failures:
            return GuardrailValidationResult(
                answer=get_fallback_response(
                    _map_validator_name(blocking_failures[0]),
                    has_sources=bool(source_list),
                ),
                passed=False,
                used_fallback=True,
                violations=blocking_failures,
            )

        validated = outcome.validated_output if outcome.validated_output is not None else response
        return GuardrailValidationResult(
            answer=self._ensure_disclaimer(validated),
            passed=True,
        )

    @staticmethod
    def _ensure_disclaimer(response: str) -> str:
        if LEGAL_DISCLAIMER in response:
            return response
        return response.rstrip() + DISCLAIMER_FOOTER


_VALIDATOR_NAME_MAP = {
    "LegalAdviceDetector": "legal/advice-detector",
    "CitationRequiredValidator": "legal/citation-required",
    "UnsupportedClaimDetector": "legal/unsupported-claims",
}


def _map_validator_name(class_name: str) -> str:
    return _VALIDATOR_NAME_MAP.get(class_name, class_name)

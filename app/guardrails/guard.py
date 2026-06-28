"""Guardrails AI Guard composition for legal document responses."""

from __future__ import annotations

import os

from guardrails import Guard

from app.guardrails.validators import (
    CitationRequiredValidator,
    LegalAdviceDetector,
    UnsupportedClaimDetector,
)

# Prefer synchronous validation in API handlers.
os.environ.setdefault("GUARDRAILS_RUN_SYNC", "true")

BLOCKING_VALIDATOR_NAMES: frozenset[str] = frozenset(
    {
        "LegalAdviceDetector",
        "CitationRequiredValidator",
        "UnsupportedClaimDetector",
    }
)


def create_legal_guard() -> Guard:
    """Build a Guard pipeline for post-response legal safety checks."""
    return Guard().use(
        LegalAdviceDetector(on_fail="refrain"),
        CitationRequiredValidator(on_fail="refrain"),
        UnsupportedClaimDetector(on_fail="refrain"),
    )

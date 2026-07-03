"""Guardrails AI Guard composition for legal document responses."""

from __future__ import annotations

import os

from guardrails import Guard

from app.core.config import settings
from app.guardrails.validators import (
    CitationRequiredValidator,
    LegalAdviceDetector,
    UnsupportedClaimDetector,
)

# Guardrails reads this env var at import time; keep it aligned with settings.
os.environ.setdefault("GUARDRAILS_RUN_SYNC", str(settings.GUARDRAILS_RUN_SYNC).lower())

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

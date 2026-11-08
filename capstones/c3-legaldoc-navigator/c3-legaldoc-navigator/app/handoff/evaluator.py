"""Escalation trigger evaluation for human handoff."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.config import settings
from app.guardrails.constants import CITATION_PATTERNS, INSUFFICIENT_INFO_PHRASES, LEGAL_ADVICE_PATTERNS

_CITATION_RE = re.compile("|".join(f"(?:{p})" for p in CITATION_PATTERNS), re.IGNORECASE)
_ADVICE_RE = re.compile("|".join(f"(?:{p})" for p in LEGAL_ADVICE_PATTERNS), re.IGNORECASE)

HIGH_RISK_QUERY_PATTERNS: tuple[str, ...] = (
    r"\bshould i sue\b",
    r"\bcan i sue\b",
    r"\bam i liable\b",
    r"\bwhat should i do\b",
    r"\bis this legal\b",
    r"\bdo i have a case\b",
    r"\bwill i win\b",
    r"\bwill i lose\b",
    r"\bshould i hire a lawyer\b",
    r"\bshould i sign\b",
    r"\bcan i break\b",
    r"\bcan i terminate\b",
)

_HIGH_RISK_QUERY_RE = re.compile(
    "|".join(f"(?:{p})" for p in HIGH_RISK_QUERY_PATTERNS),
    re.IGNORECASE,
)


@dataclass
class EscalationEvaluation:
    """Result of evaluating whether a query interaction should be escalated."""

    should_escalate: bool
    reasons: list[str] = field(default_factory=list)


def _is_insufficient_info_answer(answer: str) -> bool:
    lowered = answer.lower()
    return any(phrase in lowered for phrase in INSUFFICIENT_INFO_PHRASES)


def _has_supporting_citations(answer: str, sources: list[dict]) -> bool:
    if _is_insufficient_info_answer(answer):
        return True
    if not sources:
        return False
    return bool(_CITATION_RE.search(answer))


def is_low_confidence(confidence_score: float) -> bool:
    return confidence_score < settings.HANDOFF_CONFIDENCE_THRESHOLD


def is_high_risk_legal_advice_query(question: str) -> bool:
    if _HIGH_RISK_QUERY_RE.search(question):
        return True
    return bool(_ADVICE_RE.search(question))


def evaluate_escalation_triggers(
    *,
    question: str,
    answer: str,
    confidence_score: float,
    sources: list[dict],
) -> EscalationEvaluation:
    """Determine whether a query interaction warrants human handoff."""
    reasons: list[str] = []

    if is_low_confidence(confidence_score):
        reasons.append(
            f"confidence_score below threshold "
            f"({confidence_score:.4f} < {settings.HANDOFF_CONFIDENCE_THRESHOLD})"
        )

    if not _has_supporting_citations(answer, sources):
        reasons.append("no supporting citations")

    if is_high_risk_legal_advice_query(question):
        reasons.append("high-risk legal advice requested")

    return EscalationEvaluation(
        should_escalate=bool(reasons),
        reasons=reasons,
    )

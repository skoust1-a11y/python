"""Multi-signal confidence scoring for RAG answers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from llama_index.core.schema import NodeWithScore

from app.core.config import settings
from app.guardrails.constants import CITATION_PATTERNS, INSUFFICIENT_INFO_PHRASES

_CITATION_RE = re.compile("|".join(f"(?:{p})" for p in CITATION_PATTERNS), re.IGNORECASE)
_SOURCE_LABEL_RE = re.compile(r"\[Source\s+(\d+)\]", re.IGNORECASE)

# Component weights (must sum to 1.0)
_WEIGHT_RETRIEVAL = 0.35
_WEIGHT_CHUNK_SUPPORT = 0.15
_WEIGHT_CITATION = 0.30
_WEIGHT_LLM = 0.20

# Level thresholds on the composite 0–1 score
_LEVEL_HIGH = 0.75
_LEVEL_MEDIUM = 0.50

VERIFICATION_NOTICE = (
    "This answer has low confidence. Please verify the information manually "
    "before relying on it."
)


class ConfidenceLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass(frozen=True)
class ConfidenceBreakdown:
    """Per-signal scores that compose the final confidence value."""

    retrieval_similarity: float
    chunk_support: float
    citation_quality: float
    llm_confidence: float


@dataclass(frozen=True)
class ConfidenceResult:
    """Composite confidence assessment for a query answer."""

    score: float
    level: ConfidenceLevel
    breakdown: ConfidenceBreakdown
    verification_notice: str | None = None


def compute_confidence_score(nodes: list[NodeWithScore]) -> float:
    """
    Derive a 0–1 retrieval similarity score from ranked nodes.

    Kept for backward compatibility; prefer ``compute_confidence`` for the
    full multi-signal assessment.
    """
    scores = _extract_scores_from_nodes(nodes)
    return _rank_weighted_average(scores)


def compute_confidence(
    *,
    answer: str,
    sources: list[dict[str, Any]],
    retrieved_count: int,
    routing_confidence: float = 1.0,
    guardrails_passed: bool = True,
    top_k: int | None = None,
) -> ConfidenceResult:
    """
    Compute composite confidence from retrieval, chunk support, citations, and LLM signals.

    Returns a numerical score (0–1), a categorical level (High/Medium/Low), and
    an optional verification notice when confidence is Low.
    """
    effective_top_k = top_k or settings.TOP_K_RETRIEVAL

    retrieval = compute_retrieval_relevance(sources)
    chunk_support = _score_chunk_support(retrieved_count, effective_top_k)
    citation = _score_citation_quality(answer, sources)
    llm = _score_llm_confidence(
        answer,
        routing_confidence=routing_confidence,
        guardrails_passed=guardrails_passed,
    )

    composite = (
        retrieval * _WEIGHT_RETRIEVAL
        + chunk_support * _WEIGHT_CHUNK_SUPPORT
        + citation * _WEIGHT_CITATION
        + llm * _WEIGHT_LLM
    )
    score = round(min(max(composite, 0.0), 1.0), 4)
    level = _classify_level(score)

    return ConfidenceResult(
        score=score,
        level=level,
        breakdown=ConfidenceBreakdown(
            retrieval_similarity=round(retrieval, 4),
            chunk_support=round(chunk_support, 4),
            citation_quality=round(citation, 4),
            llm_confidence=round(llm, 4),
        ),
        verification_notice=VERIFICATION_NOTICE if level is ConfidenceLevel.LOW else None,
    )


def classify_confidence_level(score: float) -> ConfidenceLevel:
    """Map a 0–1 score to High, Medium, or Low."""
    if score >= _LEVEL_HIGH:
        return ConfidenceLevel.HIGH
    if score >= _LEVEL_MEDIUM:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def _classify_level(score: float) -> ConfidenceLevel:
    return classify_confidence_level(score)


def _extract_scores_from_nodes(nodes: list[NodeWithScore]) -> list[float]:
    if not nodes:
        return []
    raw = [float(node.score or 0.0) for node in nodes]
    return [_normalize_retrieval_score(score) for score in raw]


def _extract_scores_from_sources(sources: list[dict[str, Any]]) -> list[float]:
    if not sources:
        return []
    raw = [float(source.get("score") or 0.0) for source in sources]
    return [_normalize_retrieval_score(score) for score in raw]


def _normalize_retrieval_score(score: float) -> float:
    """Map cosine, SQL fixed, and RRF scores onto a common 0–1 scale."""
    if score <= 0.0:
        return 0.0
    # RRF fused scores are typically well below 0.15
    if score < 0.15:
        return min(score * 20.0, 1.0)
    return min(score, 1.0)


def _rank_weighted_average(scores: list[float]) -> float:
    if not scores:
        return 0.0
    weights = [1.0 / (index + 1) for index in range(len(scores))]
    weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
    total_weight = sum(weights)
    normalized = weighted_sum / total_weight if total_weight else 0.0
    return round(min(max(normalized, 0.0), 1.0), 4)


def compute_retrieval_relevance(sources: list[dict[str, Any]]) -> float:
    """Public helper: rank-weighted average of source retrieval scores (0–1)."""
    return _rank_weighted_average(_extract_scores_from_sources(sources))


def _score_chunk_support(retrieved_count: int, top_k: int) -> float:
    if retrieved_count <= 0:
        return 0.0
    if top_k <= 0:
        return 1.0 if retrieved_count > 0 else 0.0
    ratio = retrieved_count / top_k
    return min(ratio, 1.0)


def _is_insufficient_info_answer(answer: str) -> bool:
    lowered = answer.lower()
    return any(phrase in lowered for phrase in INSUFFICIENT_INFO_PHRASES)


def _score_citation_quality(answer: str, sources: list[dict[str, Any]]) -> float:
    if _is_insufficient_info_answer(answer):
        return 1.0

    if not sources:
        return 0.0

    labels_in_answer = set(_SOURCE_LABEL_RE.findall(answer))
    available_labels = {
        match.group(1)
        for source in sources
        for match in [_SOURCE_LABEL_RE.search(source.get("citation_label", ""))]
        if match
    }

    has_any_citation = bool(_CITATION_RE.search(answer))

    if not has_any_citation:
        return 0.1

    if not available_labels:
        return 0.7 if has_any_citation else 0.1

    if not labels_in_answer:
        return 0.4 if has_any_citation else 0.1

    matched = labels_in_answer & available_labels
    coverage = len(matched) / len(available_labels)
    density_bonus = min(len(labels_in_answer) / max(len(available_labels), 1), 1.0)
    return min(0.5 * coverage + 0.5 * density_bonus, 1.0)


def _score_llm_confidence(
    answer: str,
    *,
    routing_confidence: float,
    guardrails_passed: bool,
) -> float:
    if _is_insufficient_info_answer(answer):
        return 0.2

    base = min(max(float(routing_confidence), 0.0), 1.0)
    if not guardrails_passed:
        base *= 0.5
    return base

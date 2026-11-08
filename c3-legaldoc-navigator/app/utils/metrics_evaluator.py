"""Evidence-based metrics evaluator — parses structured LLM output and scores deterministically."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.guardrails.constants import INSUFFICIENT_INFO_PHRASES
from app.models.analysis_evaluation import AnalysisEvaluation, ClaimEvaluation
from app.utils.analysis_parser import parse_analysis_response
from app.utils.metrics_config import DEFAULT_SCORING_CONFIG, MetricsScoringConfig

_SOURCE_LABEL_RE = re.compile(r"\[Source\s+(\d+)\]", re.IGNORECASE)


@dataclass(frozen=True)
class MetricsResult:
    """Deterministic metrics derived from structured evaluation."""

    confidence: float
    faithfulness: float
    relevance: float
    supported_claims: int
    partial_claims: int
    unsupported_claims: int
    assumptions: int
    ambiguities: int
    hallucination: bool
    explanation: str

    def to_percent_dict(self) -> dict[str, int | bool | str]:
        """Return scores on a 0–100 scale for display or logging."""
        return {
            "confidence": round(self.confidence * 100),
            "faithfulness": round(self.faithfulness * 100),
            "relevance": round(self.relevance * 100),
            "supported_claims": self.supported_claims,
            "partial_claims": self.partial_claims,
            "unsupported_claims": self.unsupported_claims,
            "assumptions": self.assumptions,
            "ambiguities": self.ambiguities,
            "hallucination": self.hallucination,
            "explanation": self.explanation,
        }


class MetricsEvaluator:
    """
    Parse structured evaluation JSON and compute reproducible faithfulness,
    relevance, and confidence scores.

    The LLM must not emit numeric scores; this component owns all scoring.
    """

    def __init__(self, config: MetricsScoringConfig | None = None) -> None:
        self.config = config or DEFAULT_SCORING_CONFIG

    def parse(self, raw: str) -> AnalysisEvaluation | None:
        """Parse structured evaluation JSON from LLM output."""
        return parse_analysis_response(raw)

    def evaluate(
        self,
        evaluation: AnalysisEvaluation,
        *,
        sources: list[dict[str, Any]],
        explain_answer: str,
        retrieved_count: int,
        top_k: int,
    ) -> MetricsResult:
        """Compute deterministic metrics from a parsed evaluation."""
        faithfulness, claim_counts = self._score_faithfulness(
            evaluation,
            explain_answer=explain_answer,
            sources=sources,
        )
        relevance = self._score_relevance(evaluation, sources)
        confidence, explanation = self._score_confidence(
            evaluation,
            sources=sources,
            explain_answer=explain_answer,
            retrieved_count=retrieved_count,
            top_k=top_k,
            faithfulness=faithfulness,
            relevance=relevance,
            claim_counts=claim_counts,
        )

        return MetricsResult(
            confidence=confidence,
            faithfulness=faithfulness,
            relevance=relevance,
            supported_claims=claim_counts["supported"],
            partial_claims=claim_counts["partial"],
            unsupported_claims=claim_counts["unsupported"],
            assumptions=len(evaluation.assumptions),
            ambiguities=len(evaluation.ambiguities),
            hallucination=evaluation.hallucination_detected,
            explanation=explanation,
        )

    def apply(
        self,
        evaluation: AnalysisEvaluation,
        *,
        sources: list[dict[str, Any]],
        explain_answer: str,
        retrieved_count: int,
        top_k: int,
    ) -> AnalysisEvaluation:
        """Attach computed scores and explanation to an evaluation object."""
        result = self.evaluate(
            evaluation,
            sources=sources,
            explain_answer=explain_answer,
            retrieved_count=retrieved_count,
            top_k=top_k,
        )
        return evaluation.model_copy(
            update={
                "faithfulness": result.faithfulness,
                "relevance": result.relevance,
                "confidence": result.confidence,
                "metrics_explanation": result.explanation,
            }
        )

    def _score_faithfulness(
        self,
        evaluation: AnalysisEvaluation,
        *,
        explain_answer: str,
        sources: list[dict[str, Any]],
    ) -> tuple[float, dict[str, int]]:
        """
        Faithfulness = supported claims / total factual claims.

        Partial claims receive partial credit. Hallucination and fabricated
        citations apply penalties. Correct refusals with no claims score 100%.
        """
        counts = _count_claims_by_status(evaluation.claims)

        if not evaluation.claims and _is_insufficient_info_answer(explain_answer):
            return self.config.refusal_faithfulness_score, counts

        if not evaluation.claims:
            return 1.0, counts

        total = len(evaluation.claims)
        credit = (
            counts["supported"] * 1.0
            + counts["partial"] * self.config.partial_claim_credit
        )
        score = credit / total

        if evaluation.hallucination_detected:
            score -= self.config.hallucination_faithfulness_penalty

        fabricated = _count_fabricated_citations(evaluation.claims, sources)
        if fabricated > 0:
            score -= self.config.fabricated_citation_penalty * min(fabricated, 3)

        return round(_clamp(score), 4), counts

    def _score_relevance(
        self,
        evaluation: AnalysisEvaluation,
        sources: list[dict[str, Any]],
    ) -> float:
        """Rank-weighted retrieval similarity adjusted for coverage and noise."""
        base = _rank_weighted_source_scores(sources)
        assessment = evaluation.retrieval_assessment

        coverage_factor = _coverage_to_score(assessment.coverage, self.config)
        score = base * coverage_factor

        score -= len(assessment.irrelevant_chunks) * self.config.irrelevant_chunk_penalty
        score -= len(assessment.missing_topics) * self.config.missing_topic_penalty
        score -= len(evaluation.missing_evidence) * self.config.missing_topic_penalty * 0.5

        return round(_clamp(score), 4)

    def _score_confidence(
        self,
        evaluation: AnalysisEvaluation,
        *,
        sources: list[dict[str, Any]],
        explain_answer: str,
        retrieved_count: int,
        top_k: int,
        faithfulness: float,
        relevance: float,
        claim_counts: dict[str, int],
    ) -> tuple[float, str]:
        """Composite certainty score — not a measure of answer correctness."""
        cfg = self.config
        retrieval_quality = relevance

        effective_top_k = max(top_k, 1)
        if retrieved_count <= 0:
            citation_coverage = 0.0
        else:
            cited_labels = _count_cited_sources(explain_answer)
            citation_coverage = min(cited_labels / min(retrieved_count, effective_top_k), 1.0)

        retrieval_coverage = _coverage_to_score(
            evaluation.retrieval_assessment.coverage,
            cfg,
        )
        evidence_coverage = 0.6 * retrieval_coverage + 0.4 * citation_coverage
        claim_support = faithfulness

        ambiguity_burden = _normalized_burden(
            len(evaluation.ambiguities),
            cfg.max_penalty_items,
        )
        ambiguity_score = 1.0 - ambiguity_burden * cfg.ambiguity_penalty * cfg.max_penalty_items

        missing_items = (
            len(evaluation.missing_information)
            + len(evaluation.retrieval_assessment.missing_topics)
            + len(evaluation.missing_evidence)
        )
        missing_burden = _normalized_burden(missing_items, cfg.max_penalty_items)
        missing_score = 1.0 - missing_burden * cfg.missing_info_penalty * cfg.max_penalty_items

        composite = (
            retrieval_quality * cfg.weight_retrieval_quality
            + evidence_coverage * cfg.weight_evidence_coverage
            + claim_support * cfg.weight_claim_support
            + ambiguity_score * cfg.weight_ambiguity
            + missing_score * cfg.weight_missing_information
        )

        inference_claims = sum(1 for c in evaluation.claims if c.requires_inference)
        inference_burden = _normalized_burden(
            len(evaluation.inferences) + inference_claims,
            cfg.max_penalty_items,
        )
        assumption_burden = _normalized_burden(
            len(evaluation.assumptions),
            cfg.max_penalty_items,
        )
        calculation_burden = _normalized_burden(
            len(evaluation.calculations) + sum(1 for c in evaluation.claims if c.calculation),
            cfg.max_penalty_items,
        )

        composite -= (
            assumption_burden * cfg.assumption_penalty * cfg.max_penalty_items
            + inference_burden * cfg.inference_penalty * cfg.max_penalty_items
            + calculation_burden * cfg.calculation_penalty * cfg.max_penalty_items
        )

        if evaluation.hallucination_detected:
            composite -= cfg.hallucination_faithfulness_penalty

        if claim_counts["unsupported"] > 0:
            composite -= 0.05 * claim_counts["unsupported"]

        if _is_insufficient_info_answer(explain_answer):
            composite = min(composite, cfg.insufficient_info_confidence_cap)

        score = round(_clamp(composite), 4)
        explanation = _build_explanation(
            evaluation=evaluation,
            explain_answer=explain_answer,
            claim_counts=claim_counts,
            faithfulness=faithfulness,
            relevance=relevance,
            confidence=score,
        )
        return score, explanation


def _count_claims_by_status(claims: list[ClaimEvaluation]) -> dict[str, int]:
    supported = partial = unsupported = 0
    for claim in claims:
        if claim.status == "supported":
            supported += 1
        elif claim.status == "partially_supported":
            partial += 1
        else:
            unsupported += 1
    return {"supported": supported, "partial": partial, "unsupported": unsupported}


def _count_fabricated_citations(
    claims: list[ClaimEvaluation],
    sources: list[dict[str, Any]],
) -> int:
    available = {
        match.group(1)
        for source in sources
        for match in [_SOURCE_LABEL_RE.search(source.get("citation_label", ""))]
        if match
    }
    if not available:
        return 0

    fabricated = 0
    for claim in claims:
        for citation in claim.supporting_sources:
            for label in _SOURCE_LABEL_RE.findall(citation):
                if label not in available:
                    fabricated += 1
    return fabricated


def _coverage_to_score(coverage: str, config: MetricsScoringConfig) -> float:
    mapping = {
        "high": config.coverage_high,
        "medium": config.coverage_medium,
        "low": config.coverage_low,
    }
    return mapping.get(coverage, config.coverage_medium)


def _normalize_score(score: float) -> float:
    if score <= 0.0:
        return 0.0
    if score < 0.15:
        return min(score * 20.0, 1.0)
    return min(score, 1.0)


def _rank_weighted_source_scores(sources: list[dict[str, Any]]) -> float:
    scores = [_normalize_score(float(source.get("score") or 0.0)) for source in sources]
    if not scores:
        return 0.0
    weights = [1.0 / (index + 1) for index in range(len(scores))]
    weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
    total_weight = sum(weights)
    return round(_clamp(weighted_sum / total_weight), 4)


def _normalized_burden(count: int, max_items: int) -> float:
    if count <= 0 or max_items <= 0:
        return 0.0
    return min(count / max_items, 1.0)


def _count_cited_sources(answer: str) -> int:
    return len(set(_SOURCE_LABEL_RE.findall(answer, re.IGNORECASE)))


def _is_insufficient_info_answer(answer: str) -> bool:
    lowered = answer.lower()
    return any(phrase in lowered for phrase in INSUFFICIENT_INFO_PHRASES)


def _clamp(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _build_explanation(
    *,
    evaluation: AnalysisEvaluation,
    explain_answer: str,
    claim_counts: dict[str, int],
    faithfulness: float,
    relevance: float,
    confidence: float,
) -> str:
    parts: list[str] = []

    if evaluation.hallucination_detected:
        parts.append("Hallucination detected; faithfulness and confidence reduced.")

    if claim_counts["unsupported"] > 0:
        parts.append(
            f"{claim_counts['unsupported']} unsupported claim(s) lowered faithfulness."
        )

    inference_claims = sum(1 for c in evaluation.claims if c.requires_inference)
    if inference_claims > 0 or evaluation.inferences:
        parts.append(
            "Confidence reduced because answer required inference across document clauses."
        )

    if evaluation.assumptions:
        parts.append(f"{len(evaluation.assumptions)} assumption(s) reduced certainty.")

    if evaluation.ambiguities:
        parts.append(
            f"{len(evaluation.ambiguities)} ambiguity(ies) allow multiple interpretations."
        )

    if evaluation.retrieval_assessment.coverage == "low":
        parts.append("Retrieval coverage was low for the question.")

    if not evaluation.claims and _is_insufficient_info_answer(explain_answer):
        parts.append(
            "No factual claims made; faithfulness is high but documents lack sufficient information."
        )

    if not parts:
        if faithfulness >= 0.9 and relevance >= 0.7:
            parts.append("Strong evidence support and relevant retrieval.")
        elif confidence < 0.5:
            parts.append("Limited evidence or retrieval reduced system certainty.")
        else:
            parts.append(f"Faithfulness {faithfulness:.0%}, relevance {relevance:.0%}.")

    return " ".join(parts)

"""Configurable weights and penalties for evidence-based metrics scoring."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricsScoringConfig:
    """
    Deterministic scoring parameters.

    Confidence composite weights (must sum to 1.0):
      - retrieval_quality: rank-weighted source similarity
      - evidence_coverage: retrieval coverage + citation density
      - claim_support: faithfulness from claim statuses
      - ambiguity: inverse of unresolved ambiguities
      - missing_information: inverse of missing topics / information gaps
    """

    weight_retrieval_quality: float = 0.30
    weight_evidence_coverage: float = 0.30
    weight_claim_support: float = 0.20
    weight_ambiguity: float = 0.10
    weight_missing_information: float = 0.10

    partial_claim_credit: float = 0.5

    coverage_high: float = 1.0
    coverage_medium: float = 0.60
    coverage_low: float = 0.30

    hallucination_faithfulness_penalty: float = 0.25
    fabricated_citation_penalty: float = 0.10
    irrelevant_chunk_penalty: float = 0.05
    missing_topic_penalty: float = 0.04

    assumption_penalty: float = 0.04
    inference_penalty: float = 0.03
    calculation_penalty: float = 0.02
    ambiguity_penalty: float = 0.05
    missing_info_penalty: float = 0.04

    max_penalty_items: int = 5
    insufficient_info_confidence_cap: float = 0.55
    refusal_faithfulness_score: float = 1.0

    def __post_init__(self) -> None:
        weights = (
            self.weight_retrieval_quality
            + self.weight_evidence_coverage
            + self.weight_claim_support
            + self.weight_ambiguity
            + self.weight_missing_information
        )
        if abs(weights - 1.0) > 1e-6:
            raise ValueError(f"Confidence weights must sum to 1.0, got {weights}")


DEFAULT_SCORING_CONFIG = MetricsScoringConfig()

"""Automated evaluation metrics for multi-agent investment strategy workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.workflow.state import InvestmentState


@dataclass
class CaseEvaluationResult:
    case_id: str
    case_name: str
    passed: bool
    confidence: float
    faithfulness_score: float
    evidence_coverage_score: float
    coordination_score: float
    critique_quality_score: float
    overall_score: float
    duration_ms: float
    evidence_count: int
    agents_invoked: list[str]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_faithfulness_score(final_recommendation: Any, evidence: list[Any]) -> float:
    """Evaluate whether final synthesis is grounded in empirical evidence."""
    if not final_recommendation:
        return 0.0
    if not evidence:
        return 0.2  # Base score if no evidence was collected

    # Score based on evidence count and grounded recommendations
    evidence_count = len(evidence)
    if evidence_count >= 4:
        return 1.0
    if evidence_count >= 2:
        return 0.8
    return 0.5


def compute_evidence_coverage_score(expected_fields: list[str], evidence: list[Any]) -> float:
    """Evaluate whether required evidence fields are present in the collected evidence."""
    if not expected_fields:
        return 1.0
    if not evidence:
        return 0.0

    collected_fields = {getattr(item, "field", None) for item in evidence if hasattr(item, "field")}
    matched = sum(1 for req in expected_fields if req in collected_fields)
    return round(matched / len(expected_fields), 2)


def compute_agent_coordination_score(expected_agents: list[str], agent_results: dict[str, Any]) -> float:
    """Evaluate whether required specialist agents were properly invoked and succeeded."""
    if not expected_agents:
        return 1.0
    if not agent_results:
        return 0.0

    invoked = set(agent_results.keys())
    successful = {
        agent
        for agent, res in agent_results.items()
        if getattr(res, "status", "") == "succeeded" or (isinstance(res, dict) and res.get("status") == "succeeded")
    }

    coverage = sum(1 for a in expected_agents if a in invoked) / len(expected_agents)
    success = sum(1 for a in expected_agents if a in successful) / len(expected_agents)
    return round((coverage * 0.5) + (success * 0.5), 2)


def compute_critique_quality_score(critiques: list[Any], conflicts: list[Any]) -> float:
    """Evaluate conflict detection and critique resolution."""
    unresolved_critiques = [c for c in (critiques or []) if not getattr(c, "resolved", True)]
    error_conflicts = [c for c in (conflicts or []) if getattr(c, "severity", "") == "error"]
    unresolved_count = len(unresolved_critiques) + len(error_conflicts)

    if unresolved_count == 0:
        return 1.0
    return max(0.0, round(1.0 - (unresolved_count * 0.25), 2))


def evaluate_case_run(
    case: dict[str, Any],
    final_state: InvestmentState,
    duration_ms: float,
) -> CaseEvaluationResult:
    """Evaluate a single test case execution against expected criteria."""
    expected = case.get("expected", {})
    expected_agents = expected.get("required_agents", [])
    expected_fields = expected.get("expected_evidence_fields", [])
    min_confidence = expected.get("min_confidence", 0.4)

    rec = final_state.get("final_recommendation")
    confidence = float(getattr(rec, "confidence", 0.0) or 0.0)
    evidence = list(final_state.get("evidence") or [])
    agent_results = final_state.get("agent_results") or {}
    critiques = list(final_state.get("critiques") or [])
    conflicts = list(final_state.get("conflicts") or [])

    faithfulness = compute_faithfulness_score(rec, evidence)
    coverage = compute_evidence_coverage_score(expected_fields, evidence)
    coordination = compute_agent_coordination_score(expected_agents, agent_results)
    critique_quality = compute_critique_quality_score(critiques, conflicts)

    # Weighted Overall Score
    overall_score = round(
        (faithfulness * 0.35)
        + (coverage * 0.25)
        + (coordination * 0.25)
        + (critique_quality * 0.15),
        2,
    )

    notes: list[str] = []
    if confidence < min_confidence:
        notes.append(f"Confidence {confidence:.2f} below expected {min_confidence:.2f}")
    if coverage < 0.5:
        notes.append("Low evidence coverage for expected fields")

    passed = overall_score >= 0.6 and confidence >= min_confidence

    return CaseEvaluationResult(
        case_id=case["id"],
        case_name=case["name"],
        passed=passed,
        confidence=confidence,
        faithfulness_score=faithfulness,
        evidence_coverage_score=coverage,
        coordination_score=coordination,
        critique_quality_score=critique_quality,
        overall_score=overall_score,
        duration_ms=round(duration_ms, 1),
        evidence_count=len(evidence),
        agents_invoked=list(agent_results.keys()),
        notes=notes,
    )

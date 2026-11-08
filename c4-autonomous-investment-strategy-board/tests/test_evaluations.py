"""Automated unit tests for the Evaluation Benchmark Suite."""

from app.agents.base import AgentContext
from app.providers.registry import build_providers
from tests.helpers import make_settings
from evals.metrics import (
    compute_agent_coordination_score,
    compute_critique_quality_score,
    compute_evidence_coverage_score,
    compute_faithfulness_score,
    evaluate_case_run,
)
from evals.runner import load_dataset, run_evaluation_suite


def test_load_benchmark_dataset() -> None:
    dataset = load_dataset()
    assert len(dataset) >= 4
    for case in dataset:
        assert "id" in case
        assert "name" in case
        assert "request" in case
        assert "expected" in case


def test_metric_computations() -> None:
    assert compute_faithfulness_score({"summary": "Good"}, [1, 2, 3, 4]) == 1.0
    assert compute_faithfulness_score({"summary": "Good"}, []) == 0.2
    assert compute_faithfulness_score(None, []) == 0.0

    assert compute_evidence_coverage_score(["price", "pe_ratio"], []) == 0.0
    assert compute_agent_coordination_score([], {}) == 1.0
    assert compute_critique_quality_score([], []) == 1.0


def test_run_evaluation_suite_with_stub_providers() -> None:
    settings = make_settings(
        llm_provider="stub",
        market_data_provider="stub",
        fundamental_data_provider="stub",
        news_provider="stub",
    )
    context = AgentContext(providers=build_providers(settings))
    dataset = load_dataset()[:2]  # Test first 2 cases

    results = run_evaluation_suite(dataset, context=context)
    assert len(results) == 2
    for res in results:
        assert res.case_id in {c["id"] for c in dataset}
        assert isinstance(res.overall_score, float)

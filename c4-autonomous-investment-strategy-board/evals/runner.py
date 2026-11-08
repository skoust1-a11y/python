"""Benchmark evaluation runner for Autonomous Investment Strategy Board."""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from app.agents.base import AgentContext
from app.config.settings import get_settings
from app.models.portfolio import Holding, Portfolio, SymbolValidation
from app.providers.registry import build_providers
from app.workflow.graph import invoke_strategy_board
from app.workflow.state import InvestmentState, SelectedStock, UserRequest, create_investment_state
from evals.metrics import CaseEvaluationResult, evaluate_case_run

logger = logging.getLogger("evals")


def load_dataset(dataset_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load evaluation test cases from JSON dataset."""
    if dataset_path is None:
        dataset_path = Path(__file__).parent / "datasets" / "benchmark_cases.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_evaluation_state(case: dict[str, Any]) -> InvestmentState:
    """Construct an initial InvestmentState from a benchmark case definition."""
    req_data = case["request"]
    symbols = req_data.get("symbols", [])
    user_request = UserRequest(
        text=req_data["text"],
        symbols=symbols,
        analysis_type=req_data.get("analysis_type"),
        portfolio_id=req_data.get("portfolio_id"),
    )

    portfolio: Portfolio | None = None
    if symbols and len(symbols) > 1:
        # Create a mock multi-holding portfolio for portfolio evaluation cases
        weight = round(1.0 / len(symbols), 4)
        holdings = [
            Holding(
                symbol=sym,
                quantity=10.0,
                weight=weight,
                currency="USD",
                symbol_validation=SymbolValidation(normalized=sym, status="valid"),
            )
            for sym in symbols
        ]
        portfolio = Portfolio(
            id=req_data.get("portfolio_id") or "eval-pf",
            status="imported",
            name="Evaluation Benchmark Portfolio",
            holdings=holdings,
            base_currency="USD",
        )

    selected_stock = SelectedStock(symbol=symbols[0]) if len(symbols) == 1 else None

    return create_investment_state(
        request_id=f"eval-{case['id']}",
        user_request=user_request,
        portfolio=portfolio,
        selected_stock=selected_stock,
    )


def run_evaluation_suite(
    dataset: list[dict[str, Any]] | None = None,
    *,
    context: AgentContext | None = None,
) -> list[CaseEvaluationResult]:
    """Execute evaluation cases and return scored results."""
    if dataset is None:
        dataset = load_dataset()

    if context is None:
        settings = get_settings()
        providers = build_providers(settings)
        context = AgentContext(providers=providers)

    results: list[CaseEvaluationResult] = []

    print("\n" + "=" * 80)
    print(f"🚀 Running Autonomous Investment Strategy Board Evaluations ({len(dataset)} cases)")
    print("=" * 80 + "\n")

    for idx, case in enumerate(dataset, 1):
        print(f"[{idx}/{len(dataset)}] Running: {case['name']} ({case['id']})...")
        initial_state = build_evaluation_state(case)

        start_time = time.perf_counter()
        try:
            final_state = invoke_strategy_board(initial_state, context)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            result = evaluate_case_run(case, final_state, duration_ms)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            result = CaseEvaluationResult(
                case_id=case["id"],
                case_name=case["name"],
                passed=False,
                confidence=0.0,
                faithfulness_score=0.0,
                evidence_coverage_score=0.0,
                coordination_score=0.0,
                critique_quality_score=0.0,
                overall_score=0.0,
                duration_ms=round(duration_ms, 1),
                evidence_count=0,
                agents_invoked=[],
                notes=[f"Execution failed with exception: {exc}"],
            )

        results.append(result)
        status_icon = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"   {status_icon} | Score: {result.overall_score:.2f} | Confidence: {result.confidence:.2f} | Time: {result.duration_ms:.0f}ms\n")

    print_summary_report(results)
    save_evaluation_results(results)
    return results


def print_summary_report(results: list[CaseEvaluationResult]) -> None:
    """Print formatted summary table of benchmark evaluation results."""
    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    avg_score = sum(r.overall_score for r in results) / total_count if total_count else 0.0
    avg_faithfulness = sum(r.faithfulness_score for r in results) / total_count if total_count else 0.0
    avg_coverage = sum(r.evidence_coverage_score for r in results) / total_count if total_count else 0.0
    avg_coordination = sum(r.coordination_score for r in results) / total_count if total_count else 0.0

    print("=" * 80)
    print("📊 EVALUATION BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"Total Cases : {total_count}")
    print(f"Passed      : {passed_count} / {total_count} ({passed_count/total_count*100:.1f}%)")
    print(f"Mean Score  : {avg_score:.2f} / 1.00")
    print(f"Faithfulness: {avg_faithfulness:.2f}")
    print(f"Evidence Cov: {avg_coverage:.2f}")
    print(f"Coordination: {avg_coordination:.2f}")
    print("-" * 80)
    print(f"{'Case ID':<30} | {'Status':<6} | {'Score':<5} | {'Conf':<5} | {'Time (ms)':<9}")
    print("-" * 80)
    for r in results:
        status_str = "PASS" if r.passed else "FAIL"
        print(f"{r.case_id:<30} | {status_str:<6} | {r.overall_score:<5.2f} | {r.confidence:<5.2f} | {r.duration_ms:<9.0f}")
    print("=" * 80 + "\n")


def save_evaluation_results(results: list[CaseEvaluationResult], out_path: str | Path | None = None) -> None:
    """Save JSON artifact of the evaluation run."""
    if out_path is None:
        out_dir = Path(__file__).parent / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "latest_run.json"

    data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "mean_score": round(sum(r.overall_score for r in results) / len(results), 2) if results else 0.0,
        },
        "cases": [r.to_dict() for r in results],
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    run_evaluation_suite()

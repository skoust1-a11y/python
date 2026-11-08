"""Tests for RAG evaluation metrics, cost estimation, and dashboard generation."""

import json
from pathlib import Path

import pytest

from app.evaluation.cost import estimate_cost
from app.evaluation.dashboard import generate_dashboard
from app.evaluation.dataset import load_benchmark
from app.evaluation.metrics import EvaluationResult, RAGEvaluator


def test_estimate_cost_returns_positive_values():
    cost = estimate_cost(
        question="What is the termination notice period?",
        answer="Thirty days written notice is required.",
        contexts=["Either party may terminate upon thirty (30) days written notice."],
    )
    assert cost.input_tokens > 0
    assert cost.output_tokens > 0
    assert cost.total_cost_usd >= 0


def test_load_benchmark_dataset():
    path = Path(__file__).resolve().parents[1] / "data" / "evaluation" / "benchmark.json"
    dataset = load_benchmark(path)
    assert dataset.name == "legal-doc-benchmark"
    assert len(dataset.items) >= 3
    assert dataset.items[0].question
    assert dataset.items[0].ground_truth


def test_rag_evaluator_aggregate():
    evaluator = RAGEvaluator()
    results = [
        EvaluationResult(
            question="Q1",
            ground_truth="A1",
            answer="A1",
            contexts=["ctx"],
            context_precision=0.8,
            context_recall=0.7,
            faithfulness=0.9,
            answer_relevancy=0.85,
            latency_ms=1200.0,
            cost_usd=0.001,
        ),
        EvaluationResult(
            question="Q2",
            ground_truth="A2",
            answer="A2",
            contexts=["ctx"],
            context_precision=0.6,
            context_recall=0.5,
            faithfulness=0.7,
            answer_relevancy=0.75,
            latency_ms=800.0,
            cost_usd=0.002,
        ),
    ]
    summary = evaluator.aggregate(results, run_id="test-run", dataset_name="test")
    assert summary.avg_faithfulness == pytest.approx(0.8)
    assert summary.avg_latency_ms == pytest.approx(1000.0)
    assert summary.total_cost_usd == pytest.approx(0.003)
    assert "faithfulness" in summary.to_scores_dict()


def test_generate_dashboard(tmp_path):
    payload = {
        "run_id": "test-run",
        "dataset_name": "test-dataset",
        "generated_at": "2026-06-28T00:00:00+00:00",
        "summary": {
            "total_items": 1,
            "failed_items": 0,
            "avg_context_precision": 0.8,
            "avg_context_recall": 0.7,
            "avg_faithfulness": 0.9,
            "avg_answer_relevancy": 0.85,
            "avg_latency_ms": 1500.0,
            "p95_latency_ms": 1500.0,
            "total_cost_usd": 0.003,
        },
        "results": [
            {
                "question": "Test question?",
                "ground_truth": "Test answer",
                "answer": "Test answer",
                "context_precision": 0.8,
                "context_recall": 0.7,
                "faithfulness": 0.9,
                "answer_relevancy": 0.85,
                "latency_ms": 1500.0,
                "cost_usd": 0.003,
                "route": "rag",
                "error": None,
            }
        ],
    }
    results_path = tmp_path / "eval-test-run.json"
    results_path.write_text(json.dumps(payload), encoding="utf-8")

    dashboard_path = generate_dashboard(results_path)
    html = dashboard_path.read_text(encoding="utf-8")

    assert dashboard_path.exists()
    assert "RAG Evaluation Dashboard" in html
    assert "test-run" in html
    assert "chart.js" in html.lower()

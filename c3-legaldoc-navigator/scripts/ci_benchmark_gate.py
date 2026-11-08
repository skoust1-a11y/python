#!/usr/bin/env python3
"""CI-friendly benchmark gate — run evaluation and enforce quality thresholds."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.core.logging import setup_logging
from app.database.session import async_session_factory
from app.evaluation.dashboard import generate_dashboard
from app.evaluation.runner import run_benchmark
from app.evaluation.tracing import flush_traces

DEFAULT_THRESHOLDS = {
    "context_precision": 0.6,
    "context_recall": 0.6,
    "faithfulness": 0.7,
    "answer_relevancy": 0.7,
    "avg_latency_ms": settings.EVAL_LATENCY_THRESHOLD_MS,
    "total_cost_usd": settings.EVAL_COST_THRESHOLD_USD,
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run benchmark and enforce RAG quality gates for CI",
    )
    parser.add_argument("--benchmark", default=settings.EVAL_BENCHMARK_PATH)
    parser.add_argument("--output-dir", default=settings.EVAL_OUTPUT_DIR)
    parser.add_argument("--skip-ragas", action="store_true")
    parser.add_argument(
        "--min-context-precision",
        type=float,
        default=DEFAULT_THRESHOLDS["context_precision"],
    )
    parser.add_argument(
        "--min-context-recall",
        type=float,
        default=DEFAULT_THRESHOLDS["context_recall"],
    )
    parser.add_argument(
        "--min-faithfulness",
        type=float,
        default=DEFAULT_THRESHOLDS["faithfulness"],
    )
    parser.add_argument(
        "--min-answer-relevancy",
        type=float,
        default=DEFAULT_THRESHOLDS["answer_relevancy"],
    )
    parser.add_argument(
        "--max-avg-latency-ms",
        type=float,
        default=DEFAULT_THRESHOLDS["avg_latency_ms"],
    )
    parser.add_argument(
        "--max-total-cost-usd",
        type=float,
        default=DEFAULT_THRESHOLDS["total_cost_usd"],
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    async with async_session_factory() as session:
        summary, results_path = await run_benchmark(
            session,
            benchmark_path=args.benchmark,
            output_dir=args.output_dir,
            skip_ragas=args.skip_ragas,
        )

    flush_traces()
    generate_dashboard(results_path)

    failures: list[str] = []
    ragas_checks = {
        "context_precision": (summary.avg_context_precision, args.min_context_precision),
        "context_recall": (summary.avg_context_recall, args.min_context_recall),
        "faithfulness": (summary.avg_faithfulness, args.min_faithfulness),
        "answer_relevancy": (summary.avg_answer_relevancy, args.min_answer_relevancy),
    }

    if not args.skip_ragas:
        for metric, (value, threshold) in ragas_checks.items():
            if threshold is not None and (value is None or value < threshold):
                failures.append(f"{metric}={value} < {threshold}")

    if summary.avg_latency_ms > args.max_avg_latency_ms:
        failures.append(
            f"avg_latency_ms={summary.avg_latency_ms:.1f} > {args.max_avg_latency_ms}"
        )

    if summary.total_cost_usd > args.max_total_cost_usd:
        failures.append(
            f"total_cost_usd={summary.total_cost_usd:.4f} > {args.max_total_cost_usd}"
        )

    if summary.failed_items > 0:
        failures.append(f"{summary.failed_items} evaluation item(s) errored")

    print(f"Benchmark run: {summary.run_id}")
    print(f"Results: {results_path}")

    if failures:
        print("\nQuality gate FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nQuality gate PASSED")
    return 0


def main() -> None:
    setup_logging()
    args = _build_parser().parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()

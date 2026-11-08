#!/usr/bin/env python3
"""Run automated RAG benchmark evaluation with RAGAS and Langfuse."""

from __future__ import annotations

import argparse
import asyncio
import logging
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run RAG benchmark evaluation (RAGAS + Langfuse)",
    )
    parser.add_argument(
        "--benchmark",
        default=settings.EVAL_BENCHMARK_PATH,
        help="Path to benchmark JSON dataset",
    )
    parser.add_argument(
        "--output-dir",
        default=settings.EVAL_OUTPUT_DIR,
        help="Directory for evaluation result JSON files",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run identifier (auto-generated if omitted)",
    )
    parser.add_argument(
        "--skip-ragas",
        action="store_true",
        help="Skip RAGAS metric computation (pipeline + latency/cost only)",
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Skip HTML dashboard generation",
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        default=None,
        help="Exit with code 1 if avg faithfulness falls below this threshold",
    )
    return parser


def _print_summary(summary) -> None:
    print("\n=== Benchmark Summary ===")
    print(f"Run ID:              {summary.run_id}")
    print(f"Dataset:             {summary.dataset_name}")
    print(f"Items:               {summary.total_items} ({summary.failed_items} failed)")
    print(f"Context Precision:   {summary.avg_context_precision}")
    print(f"Context Recall:      {summary.avg_context_recall}")
    print(f"Faithfulness:        {summary.avg_faithfulness}")
    print(f"Answer Relevancy:    {summary.avg_answer_relevancy}")
    print(f"Avg Latency (ms):    {summary.avg_latency_ms:.1f}")
    print(f"P95 Latency (ms):    {summary.p95_latency_ms:.1f}")
    print(f"Total Cost (USD):    ${summary.total_cost_usd:.4f}")


async def _main_async(args: argparse.Namespace) -> int:
    async with async_session_factory() as session:
        summary, results_path = await run_benchmark(
            session,
            benchmark_path=args.benchmark,
            output_dir=args.output_dir,
            skip_ragas=args.skip_ragas,
            run_id=args.run_id,
        )

    flush_traces()
    _print_summary(summary)
    print(f"\nResults saved to: {results_path}")

    if not args.no_dashboard:
        dashboard_path = generate_dashboard(results_path)
        print(f"Dashboard saved to: {dashboard_path}")

    if args.fail_under is not None:
        faithfulness = summary.avg_faithfulness
        if faithfulness is None or faithfulness < args.fail_under:
            print(
                f"\nFAIL: avg faithfulness {faithfulness} "
                f"below threshold {args.fail_under}",
            )
            return 1

    if summary.failed_items > 0:
        print(f"\nWARN: {summary.failed_items} item(s) failed during evaluation")
        return 1

    return 0


def main() -> None:
    setup_logging()
    logging.getLogger("httpx").setLevel(logging.WARNING)
    args = _build_parser().parse_args()
    exit_code = asyncio.run(_main_async(args))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()

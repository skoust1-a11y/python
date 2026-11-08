#!/usr/bin/env python3
"""Generate an HTML evaluation dashboard from saved benchmark results."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.evaluation.dashboard import generate_dashboard


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate RAG evaluation dashboard")
    parser.add_argument(
        "results",
        nargs="?",
        help="Path to eval JSON file (defaults to latest in output dir)",
    )
    parser.add_argument(
        "--output",
        help="Output HTML path (defaults to same name as results with .html)",
    )
    parser.add_argument(
        "--results-dir",
        default=settings.EVAL_OUTPUT_DIR,
        help="Directory to search for latest results when no file is given",
    )
    args = parser.parse_args()

    if args.results:
        results_path = Path(args.results)
    else:
        results_dir = Path(args.results_dir)
        candidates = sorted(results_dir.glob("eval-*.json"), reverse=True)
        if not candidates:
            print(f"No evaluation results found in {results_dir}")
            raise SystemExit(1)
        results_path = candidates[0]
        print(f"Using latest results: {results_path}")

    dashboard_path = generate_dashboard(results_path, args.output)
    print(f"Dashboard generated: {dashboard_path}")


if __name__ == "__main__":
    main()

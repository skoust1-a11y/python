"""Benchmark runner — execute RAG pipeline and compute RAGAS metrics."""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.evaluation.cost import estimate_cost
from app.evaluation.dataset import BenchmarkDataset, BenchmarkItem, load_benchmark
from app.evaluation.metrics import EvaluationResult, EvaluationSummary, RAGEvaluator
from app.evaluation.tracing import log_evaluation_scores, score_trace_metric, trace_query
from app.prompts.manager import PromptManager
from app.rag.pipeline import RAGPipeline
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Run golden-set benchmarks against the RAG pipeline."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        rag_pipeline: RAGPipeline | None = None,
        evaluator: RAGEvaluator | None = None,
        skip_ragas: bool = False,
    ) -> None:
        self._session = session
        self._pipeline = rag_pipeline or RAGPipeline(
            session=session,
            llm_service=LLMService(),
            embedding_service=EmbeddingService(),
            prompt_manager=PromptManager(),
        )
        self._evaluator = evaluator or RAGEvaluator()
        self._skip_ragas = skip_ragas

    async def run_dataset(
        self,
        dataset: BenchmarkDataset,
        *,
        run_id: str | None = None,
    ) -> EvaluationSummary:
        run_id = run_id or datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        results: list[EvaluationResult] = []

        for index, item in enumerate(dataset.items, start=1):
            logger.info(
                "Evaluating %s/%s: %s",
                index,
                len(dataset.items),
                item.question[:80],
            )
            result = await self._evaluate_item(item, run_id=run_id)
            results.append(result)

        summary = self._evaluator.aggregate(
            results,
            run_id=run_id,
            dataset_name=dataset.name,
        )
        log_evaluation_scores(
            None,
            scores=summary.to_scores_dict(),
            run_name=run_id,
        )
        return summary

    async def _evaluate_item(
        self,
        item: BenchmarkItem,
        *,
        run_id: str,
    ) -> EvaluationResult:
        with trace_query(
            name="benchmark-item",
            question=item.question,
            metadata={"run_id": run_id, "tags": item.tags},
        ) as trace:
            start = time.perf_counter()
            try:
                pipeline_result = await self._pipeline.run(
                    item.question,
                    document_id=item.document_id,
                )
                latency_ms = (time.perf_counter() - start) * 1000
                cost = estimate_cost(
                    question=item.question,
                    answer=pipeline_result.answer,
                    contexts=pipeline_result.contexts,
                )

                ragas_scores: dict[str, float | None] = {}
                if not self._skip_ragas:
                    ragas_scores = self._evaluator.compute_ragas_scores(
                        question=item.question,
                        answer=pipeline_result.answer,
                        contexts=pipeline_result.contexts,
                        ground_truth=item.ground_truth,
                        reference_contexts=item.reference_contexts or None,
                    )

                result = EvaluationResult(
                    question=item.question,
                    ground_truth=item.ground_truth,
                    answer=pipeline_result.answer,
                    contexts=pipeline_result.contexts,
                    context_precision=ragas_scores.get("context_precision"),
                    context_recall=ragas_scores.get("context_recall"),
                    faithfulness=ragas_scores.get("faithfulness"),
                    answer_relevancy=ragas_scores.get("answer_relevancy"),
                    latency_ms=round(latency_ms, 2),
                    cost_usd=cost.total_cost_usd,
                    route="rag",
                )

                if trace is not None:
                    from app.evaluation.tracing import log_query_result

                    log_query_result(
                        trace,
                        answer=pipeline_result.answer,
                        sources=pipeline_result.sources,
                        confidence_score=pipeline_result.confidence_score,
                        route="rag",
                        latency_ms=result.latency_ms,
                        cost_usd=result.cost_usd,
                        metadata={"run_id": run_id},
                    )
                    for metric, value in ragas_scores.items():
                        if value is not None:
                            score_trace_metric(trace, name=metric, value=value)

                return result
            except Exception as exc:
                logger.exception("Evaluation failed for question: %s", item.question)
                return EvaluationResult(
                    question=item.question,
                    ground_truth=item.ground_truth,
                    answer="",
                    contexts=[],
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                    error=str(exc),
                )


def save_results(summary: EvaluationSummary, output_dir: str | Path | None = None) -> Path:
    """Persist evaluation summary as JSON."""
    output_dir = Path(output_dir or settings.EVAL_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "run_id": summary.run_id,
        "dataset_name": summary.dataset_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "total_items": summary.total_items,
            "failed_items": summary.failed_items,
            "avg_context_precision": summary.avg_context_precision,
            "avg_context_recall": summary.avg_context_recall,
            "avg_faithfulness": summary.avg_faithfulness,
            "avg_answer_relevancy": summary.avg_answer_relevancy,
            "avg_latency_ms": summary.avg_latency_ms,
            "p95_latency_ms": summary.p95_latency_ms,
            "total_cost_usd": summary.total_cost_usd,
        },
        "results": [
            {
                "question": r.question,
                "ground_truth": r.ground_truth,
                "answer": r.answer,
                "context_precision": r.context_precision,
                "context_recall": r.context_recall,
                "faithfulness": r.faithfulness,
                "answer_relevancy": r.answer_relevancy,
                "latency_ms": r.latency_ms,
                "cost_usd": r.cost_usd,
                "route": r.route,
                "error": r.error,
            }
            for r in summary.results
        ],
    }

    output_path = output_dir / f"eval-{summary.run_id}.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


async def run_benchmark(
    session: AsyncSession,
    *,
    benchmark_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    skip_ragas: bool = False,
    run_id: str | None = None,
) -> tuple[EvaluationSummary, Path]:
    """Load benchmark, run evaluation, and save results."""
    dataset = load_benchmark(benchmark_path or settings.EVAL_BENCHMARK_PATH)
    runner = BenchmarkRunner(session, skip_ragas=skip_ragas)
    summary = await runner.run_dataset(dataset, run_id=run_id or str(uuid.uuid4())[:8])
    output_path = save_results(summary, output_dir)
    return summary, output_path

"""RAG evaluation metrics — RAGAS scores, latency, and cost."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import settings


@dataclass
class EvaluationResult:
    """Per-question evaluation output."""

    question: str
    ground_truth: str
    answer: str
    contexts: list[str]
    context_precision: float | None = None
    context_recall: float | None = None
    faithfulness: float | None = None
    answer_relevancy: float | None = None
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    route: str = "rag"
    error: str | None = None


@dataclass
class EvaluationSummary:
    """Aggregated metrics across a benchmark run."""

    run_id: str
    dataset_name: str
    total_items: int
    failed_items: int
    avg_context_precision: float | None = None
    avg_context_recall: float | None = None
    avg_faithfulness: float | None = None
    avg_answer_relevancy: float | None = None
    avg_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    p95_latency_ms: float = 0.0
    results: list[EvaluationResult] = field(default_factory=list)

    def to_scores_dict(self) -> dict[str, float]:
        scores: dict[str, float] = {
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "total_cost_usd": self.total_cost_usd,
        }
        for key in (
            "avg_context_precision",
            "avg_context_recall",
            "avg_faithfulness",
            "avg_answer_relevancy",
        ):
            value = getattr(self, key)
            if value is not None:
                scores[key.replace("avg_", "")] = value
        return scores


def _average(values: list[float | None]) -> float | None:
    numeric = [v for v in values if v is not None]
    if not numeric:
        return None
    return sum(numeric) / len(numeric)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(len(ordered) * percentile)
    index = min(index, len(ordered) - 1)
    return ordered[index]


class RAGEvaluator:
    """Evaluate RAG pipeline quality using RAGAS and operational metrics."""

    def __init__(self, *, ragas_model: str | None = None) -> None:
        self.ragas_model = ragas_model or settings.EVAL_RAGAS_MODEL

    def _build_ragas_llm(self):
        from langchain_openai import ChatOpenAI
        from ragas.llms import LangchainLLMWrapper

        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for RAGAS evaluation")

        llm = ChatOpenAI(
            model=self.ragas_model,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )
        return LangchainLLMWrapper(llm)

    def compute_ragas_scores(
        self,
        *,
        question: str,
        answer: str,
        contexts: list[str],
        ground_truth: str,
        reference_contexts: list[str] | None = None,
    ) -> dict[str, float | None]:
        """Run RAGAS metrics for a single sample."""
        from ragas import EvaluationDataset, evaluate
        from ragas.metrics import (
            AnswerRelevancy,
            ContextPrecision,
            ContextRecall,
            Faithfulness,
        )

        sample: dict = {
            "user_input": question,
            "response": answer,
            "retrieved_contexts": contexts or [""],
            "reference": ground_truth,
        }
        if reference_contexts:
            sample["reference_contexts"] = reference_contexts

        dataset = EvaluationDataset.from_list([sample])
        llm = self._build_ragas_llm()
        metrics = [
            ContextPrecision(llm=llm),
            ContextRecall(llm=llm),
            Faithfulness(llm=llm),
            AnswerRelevancy(llm=llm),
        ]

        result = evaluate(dataset=dataset, metrics=metrics)
        row = result.to_pandas().iloc[0]

        return {
            "context_precision": _safe_float(row.get("context_precision")),
            "context_recall": _safe_float(row.get("context_recall")),
            "faithfulness": _safe_float(row.get("faithfulness")),
            "answer_relevancy": _safe_float(row.get("answer_relevancy")),
        }

    def aggregate(self, results: list[EvaluationResult], *, run_id: str, dataset_name: str) -> EvaluationSummary:
        latencies = [r.latency_ms for r in results]
        return EvaluationSummary(
            run_id=run_id,
            dataset_name=dataset_name,
            total_items=len(results),
            failed_items=sum(1 for r in results if r.error),
            avg_context_precision=_average([r.context_precision for r in results]),
            avg_context_recall=_average([r.context_recall for r in results]),
            avg_faithfulness=_average([r.faithfulness for r in results]),
            avg_answer_relevancy=_average([r.answer_relevancy for r in results]),
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0.0,
            total_cost_usd=sum(r.cost_usd for r in results),
            p95_latency_ms=_percentile(latencies, 0.95),
            results=results,
        )


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric:  # NaN check
        return None
    return numeric

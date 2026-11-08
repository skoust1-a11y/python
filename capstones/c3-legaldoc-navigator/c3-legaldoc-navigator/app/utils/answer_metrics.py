"""Evidence-based scoring for faithfulness, relevance, and confidence.

Thin wrappers around MetricsEvaluator for backward compatibility.
"""

from __future__ import annotations

from typing import Any

from app.models.analysis_evaluation import AnalysisEvaluation, RetrievalAssessment
from app.utils.metrics_evaluator import MetricsEvaluator

_default_evaluator = MetricsEvaluator()


def compute_faithfulness(evaluation: AnalysisEvaluation | None) -> float:
    """Percentage of factual claims supported by retrieved evidence."""
    if evaluation is None or not evaluation.claims:
        return 1.0

    result = _default_evaluator.evaluate(
        evaluation,
        sources=[],
        explain_answer="",
        retrieved_count=0,
        top_k=1,
    )
    return result.faithfulness


def compute_relevance(sources: list[dict[str, Any]]) -> float:
    """How relevant retrieved chunks are to the user's question (0–1)."""
    empty_eval = AnalysisEvaluation(
        retrieval_assessment=RetrievalAssessment(coverage="high"),
    )
    result = _default_evaluator.evaluate(
        empty_eval,
        sources=sources,
        explain_answer="",
        retrieved_count=len(sources),
        top_k=max(len(sources), 1),
    )
    return result.relevance


def compute_confidence_from_evidence(
    *,
    evaluation: AnalysisEvaluation | None,
    sources: list[dict[str, Any]],
    explain_answer: str,
    retrieved_count: int,
    top_k: int,
) -> float:
    """Composite confidence from retrieval, faithfulness, coverage, and inference burden."""
    eval_obj = evaluation or AnalysisEvaluation()
    result = _default_evaluator.evaluate(
        eval_obj,
        sources=sources,
        explain_answer=explain_answer,
        retrieved_count=retrieved_count,
        top_k=top_k,
    )
    return result.confidence


def apply_scores_to_evaluation(
    evaluation: AnalysisEvaluation,
    *,
    sources: list[dict[str, Any]],
    explain_answer: str,
    retrieved_count: int,
    top_k: int,
) -> AnalysisEvaluation:
    """Attach deterministic scores to a parsed evaluation object."""
    return _default_evaluator.apply(
        evaluation,
        sources=sources,
        explain_answer=explain_answer,
        retrieved_count=retrieved_count,
        top_k=top_k,
    )

"""Tests for MetricsEvaluator deterministic scoring."""

from app.utils.metrics_config import MetricsScoringConfig
from app.utils.metrics_evaluator import MetricsEvaluator
from app.models.analysis_evaluation import (
    AnalysisEvaluation,
    ClaimEvaluation,
    RetrievalAssessment,
)


def _source(score: float, label: str = "[Source 1]") -> dict:
    return {"score": score, "citation_label": label}


def _evaluator() -> MetricsEvaluator:
    return MetricsEvaluator()


def test_complete_support_high_faithfulness():
    """All claims supported → faithfulness near 100%."""
    evaluation = AnalysisEvaluation(
        claims=[
            ClaimEvaluation(claim="Payment due in 30 days", status="supported"),
            ClaimEvaluation(claim="GST is 18%", status="supported"),
        ],
        retrieval_assessment=RetrievalAssessment(coverage="high"),
    )
    result = _evaluator().evaluate(
        evaluation,
        sources=[_source(0.9, "[Source 1]"), _source(0.85, "[Source 2]")],
        explain_answer="Payment due in 30 days [Source 1]. GST is 18% [Source 2].",
        retrieved_count=2,
        top_k=5,
    )
    assert result.faithfulness == 1.0
    assert result.supported_claims == 2
    assert result.unsupported_claims == 0
    assert result.confidence > 0.5


def test_partial_support_reduces_faithfulness():
    """Partial claims receive partial credit."""
    evaluation = AnalysisEvaluation(
        claims=[
            ClaimEvaluation(claim="A", status="supported"),
            ClaimEvaluation(claim="B", status="partially_supported"),
            ClaimEvaluation(claim="C", status="unsupported"),
        ],
    )
    result = _evaluator().evaluate(
        evaluation,
        sources=[_source(0.8)],
        explain_answer="A [Source 1].",
        retrieved_count=1,
        top_k=5,
    )
    assert result.faithfulness == 0.5
    assert result.partial_claims == 1
    assert result.unsupported_claims == 1


def test_hallucination_drops_faithfulness_and_confidence():
    """Hallucination flag and unsupported claims significantly reduce scores."""
    evaluation = AnalysisEvaluation(
        claims=[
            ClaimEvaluation(claim="Fabricated clause", status="unsupported"),
            ClaimEvaluation(claim="Another false claim", status="unsupported"),
        ],
        hallucination_detected=True,
    )
    result = _evaluator().evaluate(
        evaluation,
        sources=[_source(0.9)],
        explain_answer="Fabricated clause [Source 1].",
        retrieved_count=1,
        top_k=5,
    )
    assert result.hallucination is True
    assert result.faithfulness < 0.5
    assert result.confidence < 0.5
    assert "Hallucination" in result.explanation


def test_no_evidence_correct_refusal():
    """Correct refusal with no claims → faithfulness 100%, low confidence."""
    evaluation = AnalysisEvaluation(
        claims=[],
        retrieval_assessment=RetrievalAssessment(coverage="low"),
    )
    refusal = (
        "The provided legal documents do not contain information to answer this question."
    )
    result = _evaluator().evaluate(
        evaluation,
        sources=[_source(0.2)],
        explain_answer=refusal,
        retrieved_count=1,
        top_k=5,
    )
    assert result.faithfulness == 1.0
    assert result.confidence <= 0.55
    assert "lack sufficient information" in result.explanation


def test_scenario_question_inference_reduces_confidence_not_faithfulness():
    """Multi-clause scenario: high faithfulness, reduced confidence from inference."""
    evaluation = AnalysisEvaluation(
        claims=[
            ClaimEvaluation(
                claim="Late fee applies after 30 days",
                status="supported",
                requires_inference=True,
            ),
            ClaimEvaluation(
                claim="Total with GST is 472",
                status="supported",
                requires_inference=True,
                calculation=True,
            ),
        ],
        inferences=["Combined payment, GST, and late fee clauses"],
        calculations=["400 * 1.18 = 472"],
        retrieval_assessment=RetrievalAssessment(coverage="high"),
    )
    result = _evaluator().evaluate(
        evaluation,
        sources=[
            _source(0.88, "[Source 1]"),
            _source(0.85, "[Source 2]"),
            _source(0.82, "[Source 3]"),
        ],
        explain_answer="Late fee applies [Source 1]. Total 472 [Source 2].",
        retrieved_count=3,
        top_k=5,
    )
    assert result.faithfulness == 1.0
    assert result.confidence < 0.85
    assert "inference" in result.explanation.lower()


def test_conflicting_clauses_reduce_confidence():
    """Multiple interpretations (ambiguities) lower confidence, not faithfulness."""
    evaluation = AnalysisEvaluation(
        claims=[
            ClaimEvaluation(claim="Interpretation A is valid", status="supported"),
            ClaimEvaluation(claim="Interpretation B is valid", status="supported"),
        ],
        ambiguities=["Clause 4 and Clause 7 conflict on termination notice"],
        retrieval_assessment=RetrievalAssessment(coverage="medium"),
    )
    result = _evaluator().evaluate(
        evaluation,
        sources=[_source(0.75, "[Source 1]"), _source(0.70, "[Source 2]")],
        explain_answer="Interpretation A [Source 1]. Interpretation B [Source 2].",
        retrieved_count=2,
        top_k=5,
    )
    assert result.faithfulness == 1.0
    assert result.ambiguities == 1
    assert "ambiguity" in result.explanation.lower()
    assert result.confidence < 0.8


def test_relevance_penalized_for_irrelevant_chunks_and_missing_topics():
    """Poor retrieval assessment reduces relevance."""
    evaluation = AnalysisEvaluation(
        retrieval_assessment=RetrievalAssessment(
            coverage="low",
            missing_topics=["late fee clause", "GST clause"],
            irrelevant_chunks=["[Source 3]"],
        ),
    )
    result = _evaluator().evaluate(
        evaluation,
        sources=[_source(0.8), _source(0.7), _source(0.3)],
        explain_answer="Answer [Source 1].",
        retrieved_count=3,
        top_k=5,
    )
    bare = _evaluator().evaluate(
        AnalysisEvaluation(retrieval_assessment=RetrievalAssessment(coverage="high")),
        sources=[_source(0.8), _source(0.7), _source(0.3)],
        explain_answer="Answer [Source 1].",
        retrieved_count=3,
        top_k=5,
    )
    assert result.relevance < bare.relevance


def test_fabricated_citation_penalty():
    """Citations not in retrieved sources reduce faithfulness."""
    evaluation = AnalysisEvaluation(
        claims=[
            ClaimEvaluation(
                claim="Clause exists",
                status="supported",
                supporting_sources=["[Source 99]"],
            ),
        ],
    )
    result = _evaluator().evaluate(
        evaluation,
        sources=[_source(0.9, "[Source 1]")],
        explain_answer="Clause exists [Source 99].",
        retrieved_count=1,
        top_k=5,
    )
    assert result.faithfulness < 1.0


def test_to_percent_dict():
    """Display dict uses 0–100 integer scale."""
    evaluation = AnalysisEvaluation(
        claims=[ClaimEvaluation(claim="A", status="supported")],
    )
    result = _evaluator().evaluate(
        evaluation,
        sources=[_source(0.9)],
        explain_answer="A [Source 1].",
        retrieved_count=1,
        top_k=5,
    )
    display = result.to_percent_dict()
    assert display["faithfulness"] == 100
    assert isinstance(display["explanation"], str)


def test_configurable_scoring_weights():
    """Custom config produces reproducible, different scores."""
    evaluation = AnalysisEvaluation(
        claims=[ClaimEvaluation(claim="A", status="supported")],
        assumptions=["assumed calendar days"],
    )
    strict = MetricsEvaluator(
        MetricsScoringConfig(assumption_penalty=0.20),
    )
    lenient = MetricsEvaluator(
        MetricsScoringConfig(assumption_penalty=0.01),
    )
    kwargs = dict(
        sources=[_source(0.9)],
        explain_answer="A [Source 1].",
        retrieved_count=1,
        top_k=5,
    )
    strict_score = strict.evaluate(evaluation, **kwargs).confidence
    lenient_score = lenient.evaluate(evaluation, **kwargs).confidence
    assert strict_score < lenient_score

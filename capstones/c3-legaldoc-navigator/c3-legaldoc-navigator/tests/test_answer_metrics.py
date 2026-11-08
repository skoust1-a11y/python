"""Tests for evidence-based answer metrics."""



from app.utils.answer_metrics import (

    apply_scores_to_evaluation,

    compute_confidence_from_evidence,

    compute_faithfulness,

    compute_relevance,

)

from app.models.analysis_evaluation import AnalysisEvaluation, ClaimEvaluation





def _source(score: float, label: str = "[Source 1]") -> dict:

    return {"score": score, "citation_label": label}





def test_faithfulness_all_supported():

    evaluation = AnalysisEvaluation(

        claims=[

            ClaimEvaluation(claim="A", status="supported"),

            ClaimEvaluation(claim="B", status="supported"),

        ]

    )

    assert compute_faithfulness(evaluation) == 1.0





def test_faithfulness_partial_and_unsupported():

    evaluation = AnalysisEvaluation(

        claims=[

            ClaimEvaluation(claim="A", status="supported"),

            ClaimEvaluation(claim="B", status="partially_supported"),

            ClaimEvaluation(claim="C", status="unsupported"),

        ]

    )

    assert compute_faithfulness(evaluation) == 0.5





def test_relevance_from_source_scores():

    sources = [_source(0.9), _source(0.7)]

    relevance = compute_relevance(sources)

    assert 0.7 < relevance < 0.9





def test_insufficient_info_answer_caps_confidence():

    confidence = compute_confidence_from_evidence(

        evaluation=AnalysisEvaluation(claims=[]),

        sources=[_source(0.3)],

        explain_answer="I could not find relevant information in the indexed documents.",

        retrieved_count=1,

        top_k=5,

    )

    assert confidence <= 0.55





def test_strong_evidence_raises_confidence():

    evaluation = AnalysisEvaluation(

        claims=[ClaimEvaluation(claim="GST is 18%", status="supported")],

    )

    confidence = compute_confidence_from_evidence(

        evaluation=evaluation,

        sources=[_source(0.9)],

        explain_answer="GST is 18% [Source 1].",

        retrieved_count=1,

        top_k=5,

    )

    assert confidence > 0.5





def test_apply_scores_attaches_explanation():

    evaluation = AnalysisEvaluation(

        claims=[ClaimEvaluation(claim="Test", status="supported")],

    )

    scored = apply_scores_to_evaluation(

        evaluation,

        sources=[_source(0.9)],

        explain_answer="Test [Source 1].",

        retrieved_count=1,

        top_k=5,

    )

    assert scored.faithfulness > 0

    assert scored.metrics_explanation is not None



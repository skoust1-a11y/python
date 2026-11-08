"""Tests for analysis JSON parsing."""



from app.utils.analysis_parser import format_analysis_markdown, parse_analysis_response

from app.models.analysis_evaluation import AnalysisEvaluation, ClaimEvaluation





def test_parse_analysis_response_from_json_fence():

    raw = '''```json

{

  "claims": [

    {

      "claim": "Payment is due within 30 days",

      "status": "supported",

      "evidence": ["[Source 1]"],

      "reason": "Explicit in clause",

      "requires_inference": false,

      "calculation": false

    }

  ],

  "retrieval_assessment": {

    "coverage": "high",

    "missing_topics": [],

    "irrelevant_chunks": []

  },

  "assumptions": [],

  "missing_information": [],

  "ambiguities": [],

  "hallucination_detected": false,

  "inferences": ["Combined payment and GST clauses"],

  "calculations": ["400 * 1.18 = 472"],

  "summary": "Most claims are supported."

}

```'''

    result = parse_analysis_response(raw)

    assert result is not None

    assert len(result.claims) == 1

    assert result.claims[0].status == "supported"

    assert result.claims[0].supporting_sources == ["[Source 1]"]

    assert result.retrieval_assessment.coverage == "high"

    assert result.calculations == ["400 * 1.18 = 472"]





def test_parse_partial_status_normalized():

    raw = '''```json

{"claims": [{"claim": "X", "status": "partial", "evidence": []}]}

```'''

    result = parse_analysis_response(raw)

    assert result is not None

    assert result.claims[0].status == "partially_supported"





def test_format_analysis_markdown_includes_scores():

    evaluation = AnalysisEvaluation(

        claims=[ClaimEvaluation(claim="Test claim", status="supported")],

        summary="Overall good.",

        faithfulness=0.9,

        relevance=0.8,

        confidence=0.75,

        metrics_explanation="Strong evidence support and relevant retrieval.",

    )

    markdown = format_analysis_markdown(evaluation)

    assert "Evaluation Summary" in markdown

    assert "Claim Assessment" in markdown

    assert "Metrics Explanation" in markdown

    assert "90%" in markdown



"""Parse structured analysis JSON from LLM output."""



from __future__ import annotations



import json

import re

from typing import Any



from app.models.analysis_evaluation import (

    AnalysisEvaluation,

    ClaimEvaluation,

    RetrievalAssessment,

)



_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)

_RAW_JSON_RE = re.compile(r"(\{[^{}]*\"claims\"[^{}]*\[.*?\].*?\})", re.DOTALL)





def parse_analysis_response(raw: str) -> AnalysisEvaluation | None:

    """Extract and validate the analysis JSON object from LLM output."""

    if not raw or not raw.strip():

        return None



    payload = _extract_json_payload(raw)

    if payload is None:

        return None



    try:

        data = json.loads(payload)

    except json.JSONDecodeError:

        return None



    return _build_evaluation(data)





def format_analysis_markdown(evaluation: AnalysisEvaluation) -> str:

    """Render a human-readable analysis view from structured evaluation data."""

    lines: list[str] = []



    if evaluation.summary:

        lines.append("## Evaluation Summary")

        lines.append(evaluation.summary)

        lines.append("")



    if evaluation.metrics_explanation:

        lines.append("## Metrics Explanation")

        lines.append(evaluation.metrics_explanation)

        lines.append("")



    if evaluation.claims:

        lines.append("## Claim Assessment")

        for item in evaluation.claims:

            status_label = item.status.replace("_", " ").title()

            sources = ", ".join(item.supporting_sources) if item.supporting_sources else "none"

            lines.append(f"- **{status_label}:** {item.claim}")

            if item.notes:

                lines.append(f"  - *{item.notes}* (evidence: {sources})")

            flags: list[str] = []

            if item.requires_inference:

                flags.append("requires inference")

            if item.calculation:

                flags.append("calculation")

            if flags:

                lines.append(f"  - Flags: {', '.join(flags)}")

        lines.append("")



    assessment = evaluation.retrieval_assessment

    if assessment.missing_topics or assessment.irrelevant_chunks:

        lines.append("## Retrieval Assessment")

        lines.append(f"- **Coverage:** {assessment.coverage}")

        if assessment.missing_topics:

            lines.append("- **Missing topics:**")

            for topic in assessment.missing_topics:

                lines.append(f"  - {topic}")

        if assessment.irrelevant_chunks:

            lines.append("- **Irrelevant chunks:**")

            for chunk in assessment.irrelevant_chunks:

                lines.append(f"  - {chunk}")

        lines.append("")



    sections = [

        ("Missing Information", evaluation.missing_information or evaluation.missing_evidence),

        ("Assumptions", evaluation.assumptions),

        ("Logical Inferences", evaluation.inferences),

        ("Calculations", evaluation.calculations),

        ("Ambiguities", evaluation.ambiguities),

    ]

    for title, items in sections:

        if items:

            lines.append(f"## {title}")

            for entry in items:

                lines.append(f"- {entry}")

            lines.append("")



    if evaluation.hallucination_detected:

        lines.append("## Hallucination")

        lines.append("- Potential unsupported content detected in the answer.")

        lines.append("")



    lines.append("## Scores")

    lines.append(f"- **Faithfulness:** {evaluation.faithfulness:.0%}")

    lines.append(f"- **Relevance:** {evaluation.relevance:.0%}")

    lines.append(f"- **Confidence:** {evaluation.confidence:.0%}")



    return "\n".join(lines).strip()





def _extract_json_payload(raw: str) -> str | None:

    fence_match = _JSON_FENCE_RE.search(raw)

    if fence_match:

        return fence_match.group(1).strip()



    raw_match = _RAW_JSON_RE.search(raw)

    if raw_match:

        return raw_match.group(1).strip()



    stripped = raw.strip()

    if stripped.startswith("{") and stripped.endswith("}"):

        return stripped

    return None





def _build_evaluation(data: dict[str, Any]) -> AnalysisEvaluation:

    claims = [

        _build_claim(item)

        for item in data.get("claims", [])

        if item.get("claim")

    ]



    retrieval_raw = data.get("retrieval_assessment") or {}

    retrieval_assessment = RetrievalAssessment(

        coverage=_normalize_coverage(retrieval_raw.get("coverage", "medium")),

        missing_topics=[str(v) for v in retrieval_raw.get("missing_topics", []) if v],

        irrelevant_chunks=[

            str(v) for v in retrieval_raw.get("irrelevant_chunks", []) if v

        ],

    )



    missing_information = [

        str(v) for v in data.get("missing_information", []) if v

    ]

    missing_evidence = [str(v) for v in data.get("missing_evidence", []) if v]



    return AnalysisEvaluation(

        claims=claims,

        retrieval_assessment=retrieval_assessment,

        missing_evidence=missing_evidence,

        missing_information=missing_information or missing_evidence,

        assumptions=[str(v) for v in data.get("assumptions", []) if v],

        inferences=[str(v) for v in data.get("inferences", []) if v],

        calculations=[str(v) for v in data.get("calculations", []) if v],

        ambiguities=[str(v) for v in data.get("ambiguities", []) if v],

        hallucination_detected=bool(data.get("hallucination_detected", False)),

        summary=str(data.get("summary", "")) or None,

    )





def _build_claim(item: dict[str, Any]) -> ClaimEvaluation:

    evidence = item.get("evidence") or item.get("supporting_sources") or []

    reason = item.get("reason") or item.get("notes")

    return ClaimEvaluation(

        claim=str(item.get("claim", "")),

        status=_normalize_status(item.get("status", "unsupported")),

        supporting_sources=[str(source) for source in evidence if source],

        notes=str(reason) if reason else None,

        requires_inference=bool(item.get("requires_inference", False)),

        calculation=bool(item.get("calculation", False)),

    )





def _normalize_status(value: str) -> str:

    normalized = str(value).strip().lower().replace(" ", "_").replace("-", "_")

    if normalized in {"supported", "partially_supported", "unsupported"}:

        return normalized

    if normalized in {"partial", "partially"}:

        return "partially_supported"

    return "unsupported"





def _normalize_coverage(value: str) -> str:

    normalized = str(value).strip().lower()

    if normalized in {"high", "medium", "low"}:

        return normalized

    return "medium"



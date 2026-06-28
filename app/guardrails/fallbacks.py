"""Fallback responses when legal guardrails block LLM output."""

from app.guardrails.constants import DISCLAIMER_FOOTER, LEGAL_DISCLAIMER

FALLBACK_TEMPLATES: dict[str, str] = {
    "legal/advice-detector": (
        "I cannot provide legal advice or recommendations. "
        "Based on the retrieved documents, I can only summarize factual content "
        "from the source material. Please consult a licensed attorney for guidance "
        "on your specific situation."
    ),
    "legal/citation-required": (
        "I cannot present substantive legal findings without citing the underlying "
        "source documents. Please review the source excerpts returned with this query, "
        "or rephrase your question so I can provide a properly cited summary."
    ),
    "legal/unsupported-claims": (
        "I detected factual claims that are not supported by the retrieved source "
        "material. I will not speculate beyond the indexed documents. "
        "Please verify details directly in the cited sources or consult a "
        "licensed attorney."
    ),
    "legal/evidence-required": (
        "I cannot make legal recommendations without supporting evidence from the "
        "retrieved documents. No relevant sources were available to ground a response."
    ),
    "default": (
        "I am unable to provide a validated response for this query. "
        "Please consult a licensed attorney for advice on your specific legal matter."
    ),
}


def get_fallback_response(
    validator_name: str | None = None,
    *,
    has_sources: bool = False,
) -> str:
    """Return a safe fallback message for a blocked response."""
    if validator_name == "legal/advice-detector" and not has_sources:
        body = FALLBACK_TEMPLATES["legal/evidence-required"]
    else:
        body = FALLBACK_TEMPLATES.get(validator_name or "", FALLBACK_TEMPLATES["default"])

    if LEGAL_DISCLAIMER not in body:
        body = body + DISCLAIMER_FOOTER
    return body

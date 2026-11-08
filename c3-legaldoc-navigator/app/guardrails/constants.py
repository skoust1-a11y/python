"""Shared constants for legal output guardrails."""

LEGAL_DISCLAIMER = (
    "I am an AI legal research assistant and not a substitute for professional legal advice."
)

DISCLAIMER_FOOTER = f"\n\n---\n*{LEGAL_DISCLAIMER}*"

STRICT_INSUFFICIENT_INFO_RESPONSE = (
    "I could not find sufficient information in the uploaded documents to "
    "answer this question."
)

EVIDENCE_NONE_FOUND_PHRASES: tuple[str, ...] = (
    "no relevant clauses found",
    "no evidence found",
)

INSUFFICIENT_INFO_PHRASES: tuple[str, ...] = (
    "could not find relevant",
    "could not find sufficient",
    "could not find sufficient information in the uploaded documents",
    "does not contain enough",
    "does not contain sufficient",
    "do not contain information",
    "does not contain information",
    "insufficient information",
    "not enough information",
    "no relevant information",
    "no relevant clauses found",
    "unable to answer",
    "cannot answer based on",
    "not found in the indexed",
    "not found in the provided",
    "not found in the retrieved",
) + EVIDENCE_NONE_FOUND_PHRASES

# Prescriptive language that constitutes legal advice or recommendations.
LEGAL_ADVICE_PATTERNS: tuple[str, ...] = (
    r"\byou should\b",
    r"\byou must\b",
    r"\byou need to\b",
    r"\byou ought to\b",
    r"\bi recommend\b",
    r"\bmy recommendation\b",
    r"\bi advise\b",
    r"\bmy advice\b",
    r"\bconsult a lawyer immediately\b",
    r"\btake legal action\b",
    r"\bfile a lawsuit\b",
    r"\bsue\b",
    r"\bpress charges\b",
    r"\bthis is illegal\b",
    r"\bthis is unlawful\b",
    r"\bthis violates the law\b",
    r"\byou are liable\b",
    r"\byou have no case\b",
    r"\byou will win\b",
    r"\byou will lose\b",
)

CITATION_PATTERNS: tuple[str, ...] = (
    r"\[(?:Source|S)\s*\d+\]",
    r"\bSource\s+\d+\b",
    r"\bSection\s+\d+",
    r"\bClause\s+\d+",
    r"\bArticle\s+[IVXLC\d]+",
    r"\bParagraph\s+\d+",
    r"\bExhibit\s+[A-Z\d]+",
)

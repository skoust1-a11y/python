"""Handoff summary generation for human reviewers."""

from __future__ import annotations


def generate_handoff_summary(
    *,
    question: str,
    answer: str | None,
    confidence_score: float,
    escalation_reasons: list[str],
    sources: list[dict],
    conversation_history: list[dict],
    retrieved_documents: list[dict],
) -> str:
    """Build a structured summary for human reviewers."""
    lines = [
        "Human Handoff Escalation Summary",
        "================================",
        "",
        f"Query: {question}",
        "",
    ]

    if answer:
        excerpt = answer.strip()
        if len(excerpt) > 500:
            excerpt = excerpt[:497] + "..."
        lines.extend(["Assistant Response (excerpt):", excerpt, ""])

    lines.extend(
        [
            f"Confidence Score: {confidence_score:.4f}",
            f"Escalation Triggers: {', '.join(escalation_reasons)}",
            f"Retrieved Sources: {len(sources)}",
            f"Retrieved Documents: {len(retrieved_documents)}",
            f"Conversation Turns: {len(conversation_history)}",
            "",
        ]
    )

    if conversation_history:
        lines.append("Recent Conversation:")
        for turn in conversation_history[-5:]:
            role = turn.get("role", "unknown")
            message = turn.get("message", "")
            if len(message) > 200:
                message = message[:197] + "..."
            lines.append(f"  [{role}] {message}")
        lines.append("")

    if retrieved_documents:
        lines.append("Documents Referenced:")
        for doc in retrieved_documents:
            title = doc.get("title") or doc.get("filename", "unknown")
            doc_id = doc.get("id", "n/a")
            lines.append(f"  - {title} ({doc_id})")
        lines.append("")

    if sources:
        lines.append("Source Citations:")
        from app.utils.citation_formatter import (
            format_document_citations,
            format_location_line,
        )

        for citation in format_document_citations(sources):
            lines.append(f"  - {citation.document_name}")
            for location in citation.locations:
                detail = format_location_line(location)
                if detail:
                    lines.append(f"      {detail}")
            if citation.citation_labels:
                lines.append(
                    f"      Labels: {', '.join(citation.citation_labels)}"
                )

    return "\n".join(lines).strip()

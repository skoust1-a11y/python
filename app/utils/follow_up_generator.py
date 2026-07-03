"""Generate structured follow-up questions for query responses."""

from __future__ import annotations

import re

from app.models.schemas import SourceCitation

_FOLLOW_UP_SECTION = re.compile(
    r"(?is)\n+(?:#{1,3}\s*)?"
    r"(?:(?:suggested\s+)?follow[- ]?up(?:\s+(?:research\s+)?questions?)?|suggested\s+(?:research\s+)?questions?)"
    r"\s*:?\s*\n+"
    r"(?P<body>.*?)$"
)

_BULLET_LINE = re.compile(r"^\s*(?:[-•*]|\d+[.)])\s+(.+?)\s*$")


def extract_follow_up_from_answer(answer: str) -> tuple[str, list[str]]:
    """Remove an embedded follow-up section from prose and return structured questions."""
    match = _FOLLOW_UP_SECTION.search(answer)
    if not match:
        return answer, []

    body = match.group("body")
    questions = _parse_question_lines(body)
    cleaned = answer[: match.start()].rstrip()
    return cleaned, questions


def _parse_question_lines(text: str) -> list[str]:
    questions: list[str] = []
    for line in text.splitlines():
        bullet = _BULLET_LINE.match(line)
        if bullet:
            question = bullet.group(1).strip()
            if question.endswith("?"):
                questions.append(question)
            continue
        stripped = line.strip()
        if stripped.endswith("?"):
            questions.append(stripped)
    return _dedupe(questions)


def generate_follow_up_questions(
    question: str,
    answer: str,
    sources: list[SourceCitation],
    *,
    response_mode: str,
    max_questions: int = 4,
) -> list[str]:
    """Build follow-up questions from answer text and retrieval context."""
    cleaned_answer, extracted = extract_follow_up_from_answer(answer)
    if extracted:
        return extracted[:max_questions]

    questions: list[str] = []
    topic = _shorten(question)

    for source in sources[:2]:
        doc_name = source.document_name
        questions.append(
            f"What other clauses or sections in {doc_name} relate to this question?"
        )

    if response_mode == "analysis":
        questions.append(
            f"What case law or regulatory guidance should be reviewed regarding {topic}?"
        )
        questions.append(
            "What factual assumptions in this analysis should be verified before relying on it?"
        )
    else:
        questions.append(f"Can you provide more detail about {topic}?")

    if not sources:
        questions.append("Which documents should be uploaded or reviewed to answer this more fully?")

    return _dedupe(questions)[:max_questions]


def _shorten(text: str, limit: int = 80) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique

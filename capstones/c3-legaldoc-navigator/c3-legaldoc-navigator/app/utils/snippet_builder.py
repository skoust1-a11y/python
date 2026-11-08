"""Build contextual snippets with match highlighting for keyword search."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.utils.bm25_tokenizer import tokenize_query
from app.utils.chunk_text_formatter import clean_chunk_text

_SNIPPET_WINDOW = 400
_TERM_RE_TEMPLATE = r"\b{}\b"


@dataclass(frozen=True)
class HighlightSegment:
    """A fragment of snippet text with optional keyword match."""

    text: str
    matched: bool


def build_snippet(
    text: str,
    query: str,
    *,
    max_chars: int = _SNIPPET_WINDOW,
) -> tuple[str, list[HighlightSegment]]:
    """
    Return a focused excerpt around the best-matching region and highlight terms.

    When no query terms appear in the text, the excerpt starts at the beginning.
    """
    cleaned = clean_chunk_text(text)
    if not cleaned:
        return "", []

    terms = tokenize_query(query)
    if not terms:
        excerpt = cleaned[:max_chars]
        if len(cleaned) > max_chars:
            excerpt += "..."
        return excerpt, [HighlightSegment(text=excerpt, matched=False)]

    lower_text = cleaned.lower()
    best_pos = 0
    best_hits = -1
    for term in terms:
        start = 0
        while True:
            index = lower_text.find(term, start)
            if index < 0:
                break
            window_start = max(0, index - max_chars // 3)
            window_end = min(len(cleaned), window_start + max_chars)
            window = lower_text[window_start:window_end]
            hits = sum(1 for item in terms if item in window)
            if hits > best_hits:
                best_hits = hits
                best_pos = window_start
            start = index + len(term)

    end = min(len(cleaned), best_pos + max_chars)
    excerpt = cleaned[best_pos:end]
    if best_pos > 0:
        excerpt = "..." + excerpt
    if end < len(cleaned):
        excerpt += "..."

    return excerpt, _highlight_terms(excerpt, terms)


def _highlight_terms(excerpt: str, terms: list[str]) -> list[HighlightSegment]:
    if not excerpt or not terms:
        return [HighlightSegment(text=excerpt, matched=False)]

    pattern = "|".join(
        _TERM_RE_TEMPLATE.format(re.escape(term)) for term in sorted(terms, key=len, reverse=True)
    )
    matcher = re.compile(pattern, re.IGNORECASE)
    segments: list[HighlightSegment] = []
    cursor = 0

    for match in matcher.finditer(excerpt):
        if match.start() > cursor:
            segments.append(
                HighlightSegment(text=excerpt[cursor : match.start()], matched=False)
            )
        segments.append(HighlightSegment(text=match.group(0), matched=True))
        cursor = match.end()

    if cursor < len(excerpt):
        segments.append(HighlightSegment(text=excerpt[cursor:], matched=False))

    return segments or [HighlightSegment(text=excerpt, matched=False)]

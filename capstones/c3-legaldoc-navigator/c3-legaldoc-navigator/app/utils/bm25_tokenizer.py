"""Lightweight tokenization and query parsing for BM25 sparse retrieval."""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?", re.IGNORECASE)
_QUOTED_PHRASE_RE = re.compile(r'"([^"]+)"')


def tokenize(text: str) -> list[str]:
    """Split text into lowercase alphanumeric tokens."""
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]


def tokenize_query(query: str) -> list[str]:
    """Tokenize a search query for highlighting and validation."""
    return tokenize(query)


def parse_search_query(query: str) -> tuple[str, bool]:
    """
    Parse a user query, detecting double-quoted exact phrases.

    Returns the effective search text and whether exact-phrase mode applies.
    """
    stripped = query.strip()
    match = _QUOTED_PHRASE_RE.search(stripped)
    if match:
        phrase = match.group(1).strip()
        if phrase:
            return phrase, True
    return stripped, False

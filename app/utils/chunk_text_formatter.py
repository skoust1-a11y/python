"""Shared chunk text cleaning for display and snippet generation.

Used by keyword search snippets and anywhere retrieved legal text is shown
to users. Preserves paragraph structure while removing chunking artifacts.
"""

from __future__ import annotations

import re


def clean_chunk_text(text: str) -> str:
    """Normalize whitespace while preserving paragraph breaks.

    Collapses runs of spaces/tabs within a paragraph and trims blank lines,
    but keeps ``\\n\\n`` separators so multi-paragraph chunks stay readable.
    """
    if not text:
        return ""

    paragraphs: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text):
        cleaned = " ".join(paragraph.split())
        if cleaned:
            paragraphs.append(cleaned)
    return "\n\n".join(paragraphs)

"""Shared text-structure extraction utilities for legal documents."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ingestion.models import Clause, Heading, Section

# Legal heading patterns: SECTION 1, Article II, PART A, numbered headings
HEADING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"^(?:SECTION|Section|ARTICLE|Article|PART|Part|CHAPTER|Chapter)"
        r"\s+[\dIVXLCivxlc]+[.:]?\s*(.*)$",
    ),
    re.compile(r"^\d+(?:\.\d+)*\.?\s+[A-Z][\w\s\-,]{2,}$"),
    re.compile(r"^[A-Z][A-Z0-9\s\-,]{4,}$"),
)

# Clause patterns: (a), (1), 1., 1.1., etc.
CLAUSE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\(([a-zA-Z\d]+)\)\s+(.+)$"),
    re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(.+)$"),
    re.compile(r"^([a-zA-Z]\.)\s+(.+)$"),
)


@dataclass(frozen=True)
class TextLine:
    """A single line of text with optional page context."""

    text: str
    page: int | None = None
    line_number: int | None = None
    font_size: float | None = None


class StructureExtractor:
    """Extract headings, clauses, and sections from raw text."""

    def extract_headings(self, lines: list[TextLine]) -> list[Heading]:
        headings: list[Heading] = []
        for line in lines:
            stripped = line.text.strip()
            if not stripped:
                continue
            level = self._heading_level(stripped, line.font_size)
            if level is not None:
                headings.append(
                    Heading(
                        level=level,
                        text=stripped,
                        page=line.page,
                        line_number=line.line_number,
                    )
                )
        return headings

    def extract_clauses(
        self,
        lines: list[TextLine],
        headings: list[Heading] | None = None,
    ) -> list[Clause]:
        heading_lookup = self._build_heading_lookup(lines, headings or [])
        clauses: list[Clause] = []
        for line in lines:
            stripped = line.text.strip()
            if not stripped:
                continue
            match = self._match_clause(stripped)
            if match:
                identifier, text = match
                clauses.append(
                    Clause(
                        identifier=identifier,
                        text=text,
                        parent_heading=heading_lookup.get(line.line_number),
                        page=line.page,
                        line_number=line.line_number,
                    )
                )
        return clauses

    def build_sections(
        self,
        lines: list[TextLine],
        headings: list[Heading],
        clauses: list[Clause],
    ) -> list[Section]:
        if not headings:
            full_text = "\n".join(line.text for line in lines if line.text.strip())
            if not full_text.strip():
                return []
            return [
                Section(
                    title="Document Body",
                    level=1,
                    content=full_text,
                    page_start=lines[0].page if lines else None,
                    page_end=lines[-1].page if lines else None,
                )
            ]

        sections: list[Section] = []
        sorted_headings = sorted(
            headings,
            key=lambda h: (h.line_number or 0, h.page or 0),
        )

        for idx, heading in enumerate(sorted_headings):
            start = heading.line_number or 0
            end = (
                sorted_headings[idx + 1].line_number
                if idx + 1 < len(sorted_headings)
                else None
            )
            section_lines = [
                line
                for line in lines
                if line.line_number is not None
                and line.line_number >= start
                and (end is None or line.line_number < end)
            ]
            content = "\n".join(
                line.text for line in section_lines if line.text.strip()
            )
            section_headings = [
                h for h in headings if h.line_number == heading.line_number
            ]
            section_clauses = [
                c
                for c in clauses
                if c.line_number is not None
                and c.line_number >= start
                and (end is None or c.line_number < end)
            ]
            sections.append(
                Section(
                    title=heading.text,
                    level=heading.level,
                    content=content,
                    page_start=heading.page,
                    page_end=section_lines[-1].page if section_lines else heading.page,
                    headings=section_headings,
                    clauses=section_clauses,
                )
            )
        return sections

    def infer_title(
        self,
        lines: list[TextLine],
        headings: list[Heading],
        metadata_title: str | None = None,
    ) -> str | None:
        if metadata_title and metadata_title.strip():
            return metadata_title.strip()
        if headings:
            top_level = [h for h in headings if h.level == 1]
            if top_level:
                return top_level[0].text
            return headings[0].text
        for line in lines[:20]:
            stripped = line.text.strip()
            if stripped and len(stripped) < 200:
                return stripped
        return None

    def _heading_level(self, text: str, font_size: float | None) -> int | None:
        for pattern in HEADING_PATTERNS:
            if pattern.match(text):
                if "SECTION" in text.upper() or "ARTICLE" in text.upper():
                    return 1
                if text.isupper():
                    return 1
                return 2

        if font_size is not None and font_size >= 16:
            return 1
        if font_size is not None and font_size >= 13:
            return 2
        return None

    def _match_clause(self, text: str) -> tuple[str, str] | None:
        for pattern in CLAUSE_PATTERNS:
            match = pattern.match(text)
            if match:
                return match.group(1), match.group(2)
        return None

    def _build_heading_lookup(
        self,
        lines: list[TextLine],
        headings: list[Heading],
    ) -> dict[int | None, str | None]:
        if not headings:
            return {}
        sorted_headings = sorted(
            headings,
            key=lambda h: (h.line_number or 0, h.page or 0),
        )
        lookup: dict[int | None, str | None] = {}
        current_heading: str | None = None
        heading_idx = 0
        for line in lines:
            if (
                heading_idx < len(sorted_headings)
                and line.line_number == sorted_headings[heading_idx].line_number
            ):
                current_heading = sorted_headings[heading_idx].text
                heading_idx += 1
            lookup[line.line_number] = current_heading
        return lookup

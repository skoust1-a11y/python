"""Intelligent structure-aware chunking for legal documents.

Chunks respect section, heading, and clause boundaries. Individual clauses are
never split unless they alone exceed the configured token limit, in which case
sentence boundaries are used as a last resort.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import tiktoken
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode

from app.core.config import settings
from app.ingestion.extractors import CLAUSE_PATTERNS
from app.ingestion.models import Clause, ParsedDocument, Section

SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?;])\s+")

JURISDICTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?:governed by|laws of|jurisdiction of|State of)\s+(?:the\s+)?"
        r"([A-Z][A-Za-z\s,&\-]+?)(?:\.|,|\s+without|\s+and\s+|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:England and Wales|Northern Ireland|Scotland|"
        r"New York|California|Delaware|Singapore|Hong Kong)",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True)
class LegalChunkMetadata:
    """Metadata attached to every legal document chunk."""

    document_name: str
    clause_number: str | None = None
    section: str | None = None
    heading: str | None = None
    page_number: int | None = None
    jurisdiction: str | None = None
    chunk_index: int = 0
    token_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_name": self.document_name,
            "clause_number": self.clause_number,
            "section": self.section,
            "heading": self.heading,
            "page_number": self.page_number,
            "jurisdiction": self.jurisdiction,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
        }


@dataclass
class LegalChunk:
    """A single chunk of legal text with rich structural metadata."""

    text: str
    metadata: LegalChunkMetadata


@dataclass
class _SemanticUnit:
    """Internal atomic unit used during chunk assembly."""

    text: str
    section: str | None
    heading: str | None
    clause_number: str | None
    page_number: int | None
    unit_type: str  # "heading", "clause", "paragraph"


class TokenCounter:
    """Token counting via tiktoken with character-based fallback."""

    CHARS_PER_TOKEN = 4

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self._encoding_name = encoding_name
        self._encoding = None
        self._use_fallback = False
        self._init_encoding()

    def _init_encoding(self) -> None:
        try:
            self._encoding = tiktoken.get_encoding(self._encoding_name)
        except Exception:
            self._use_fallback = True

    def count(self, text: str) -> int:
        if not text:
            return 0
        if self._use_fallback or self._encoding is None:
            return max(1, len(text) // self.CHARS_PER_TOKEN)
        return len(self._encoding.encode(text))

    def last_n_tokens(self, text: str, n: int) -> str:
        if n <= 0 or not text:
            return ""
        if self._use_fallback or self._encoding is None:
            approx_chars = n * self.CHARS_PER_TOKEN
            return text[-approx_chars:] if len(text) > approx_chars else text
        tokens = self._encoding.encode(text)
        if len(tokens) <= n:
            return text
        return self._encoding.decode(tokens[-n:])

    def slice_by_tokens(self, text: str, start: int, max_tokens: int) -> str:
        if self._use_fallback or self._encoding is None:
            char_start = start * self.CHARS_PER_TOKEN
            char_end = char_start + max_tokens * self.CHARS_PER_TOKEN
            return text[char_start:char_end]
        tokens = self._encoding.encode(text)
        return self._encoding.decode(tokens[start : start + max_tokens])

    def total_tokens(self, text: str) -> int:
        if self._use_fallback or self._encoding is None:
            return max(1, -(-len(text) // self.CHARS_PER_TOKEN))  # ceil division
        return len(self._encoding.encode(text))


class LegalDocumentChunker:
    """Structure-aware chunker for parsed legal documents.

    Chunking priority (highest to lowest):
      1. Section boundaries
      2. Heading boundaries
      3. Clause boundaries
      4. Sentence boundaries (only when a single clause exceeds max_tokens)
    """

    def __init__(
        self,
        max_tokens: int | None = None,
        overlap_tokens: int | None = None,
        token_counter: TokenCounter | None = None,
    ) -> None:
        self.max_tokens = max_tokens if max_tokens is not None else settings.CHUNK_SIZE
        self.overlap_tokens = (
            overlap_tokens if overlap_tokens is not None else settings.CHUNK_OVERLAP
        )
        self._counter = token_counter or TokenCounter()

    def chunk(
        self,
        parsed: ParsedDocument,
        *,
        jurisdiction: str | None = None,
    ) -> list[LegalChunk]:
        """Chunk a parsed document into legally-aware segments."""
        resolved_jurisdiction = (
            jurisdiction
            or parsed.metadata.jurisdiction
            or infer_jurisdiction(parsed.raw_text)
        )
        document_name = (
            parsed.title
            or parsed.metadata.title
            or parsed.metadata.filename
        )

        units = self._build_semantic_units(parsed)
        if not units:
            return []

        return self._pack_units(
            units,
            document_name=document_name,
            jurisdiction=resolved_jurisdiction,
        )

    def chunk_to_nodes(
        self,
        parsed: ParsedDocument,
        *,
        jurisdiction: str | None = None,
    ) -> list[TextNode]:
        """Chunk a parsed document and return LlamaIndex TextNode objects."""
        chunks = self.chunk(parsed, jurisdiction=jurisdiction)
        return [
            TextNode(
                text=chunk.text,
                metadata=chunk.metadata.to_dict(),
            )
            for chunk in chunks
        ]

    # ------------------------------------------------------------------
    # Semantic unit construction
    # ------------------------------------------------------------------

    def _build_semantic_units(self, parsed: ParsedDocument) -> list[_SemanticUnit]:
        if parsed.sections:
            units: list[_SemanticUnit] = []
            for section in parsed.sections:
                units.extend(self._units_from_section(section))
            return units

        if parsed.clauses:
            return [
                self._clause_unit(clause, section_title=None, heading=None)
                for clause in parsed.clauses
            ]

        return self._paragraph_units(
            parsed.raw_text,
            section=None,
            heading=None,
            page_number=parsed.metadata.page_count and 1 or None,
        )

    def _units_from_section(self, section: Section) -> list[_SemanticUnit]:
        units: list[_SemanticUnit] = []
        content = section.content.strip()
        title_embedded = bool(
            section.title and content.startswith(section.title.strip())
        )

        if section.title and not title_embedded:
            units.append(
                _SemanticUnit(
                    text=section.title,
                    section=section.title,
                    heading=section.title,
                    clause_number=None,
                    page_number=section.page_start,
                    unit_type="heading",
                )
            )

        if section.clauses:
            units.extend(self._clause_block_units(section))
        elif content:
            units.extend(
                self._paragraph_units(
                    content,
                    section=section.title,
                    heading=section.title,
                    page_number=section.page_start,
                )
            )

        return units

    def _clause_block_units(self, section: Section) -> list[_SemanticUnit]:
        """Split section content into multi-line clause blocks without breaking clauses."""
        units: list[_SemanticUnit] = []
        lines = section.content.splitlines()
        current_lines: list[str] = []
        current_clause_id: str | None = None
        current_heading = section.title
        clause_lookup = {c.identifier: c for c in section.clauses}

        def flush(clause_id: str | None) -> None:
            text = "\n".join(current_lines).strip()
            if not text:
                return
            if clause_id is not None:
                clause = clause_lookup.get(clause_id)
                units.append(
                    self._clause_unit_from_text(
                        text=text,
                        clause_number=clause_id,
                        section_title=section.title,
                        heading=(
                            clause.parent_heading if clause else current_heading
                        ),
                        page_number=(
                            clause.page if clause else section.page_start
                        ),
                    )
                )
            else:
                units.append(
                    _SemanticUnit(
                        text=text,
                        section=section.title,
                        heading=current_heading,
                        clause_number=None,
                        page_number=section.page_start,
                        unit_type="paragraph",
                    )
                )

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_lines:
                    current_lines.append("")
                continue

            clause_start = self._match_clause_start(stripped)
            if clause_start is not None:
                flush(current_clause_id)
                current_clause_id = clause_start[0]
                current_lines = [stripped]
                clause = clause_lookup.get(current_clause_id)
                if clause and clause.parent_heading:
                    current_heading = clause.parent_heading
            else:
                current_lines.append(stripped)

        flush(current_clause_id)

        if units:
            return units

        return [
            self._clause_unit_from_text(
                text=self._format_clause_text(c),
                clause_number=c.identifier,
                section_title=section.title,
                heading=c.parent_heading or section.title,
                page_number=c.page or section.page_start,
            )
            for c in section.clauses
        ]

    @staticmethod
    def _format_clause_text(clause: Clause) -> str:
        if clause.text.startswith(f"({clause.identifier})"):
            return clause.text
        if clause.text.startswith(f"{clause.identifier}."):
            return clause.text
        if re.match(r"^\([a-zA-Z\d]+\)", clause.text):
            return clause.text
        return f"({clause.identifier}) {clause.text}"

    def _clause_unit(
        self,
        clause: Clause,
        section_title: str | None,
        heading: str | None,
    ) -> _SemanticUnit:
        return self._clause_unit_from_text(
            text=self._format_clause_text(clause),
            clause_number=clause.identifier,
            section_title=section_title,
            heading=heading or clause.parent_heading,
            page_number=clause.page,
        )

    def _clause_unit_from_text(
        self,
        *,
        text: str,
        clause_number: str,
        section_title: str | None,
        heading: str | None,
        page_number: int | None,
    ) -> _SemanticUnit:
        return _SemanticUnit(
            text=text,
            section=section_title,
            heading=heading,
            clause_number=clause_number,
            page_number=page_number,
            unit_type="clause",
        )

    def _paragraph_units(
        self,
        text: str,
        *,
        section: str | None,
        heading: str | None,
        page_number: int | None,
    ) -> list[_SemanticUnit]:
        units: list[_SemanticUnit] = []
        for paragraph in re.split(r"\n\s*\n", text):
            cleaned = paragraph.strip()
            if not cleaned:
                continue
            units.append(
                _SemanticUnit(
                    text=cleaned,
                    section=section,
                    heading=heading,
                    clause_number=None,
                    page_number=page_number,
                    unit_type="paragraph",
                )
            )
        return units

    # ------------------------------------------------------------------
    # Chunk packing with overlap
    # ------------------------------------------------------------------

    def _assemble_chunk_text(self, overlap_prefix: str, body_parts: list[str]) -> str:
        body = "\n\n".join(body_parts).strip()
        if overlap_prefix and body:
            return f"{overlap_prefix}\n\n{body}".strip()
        return body or overlap_prefix

    def _fit_overlap(self, overlap_prefix: str, body: str) -> str:
        """Trim overlap so combined text stays within max_tokens."""
        if not overlap_prefix:
            return body
        combined = f"{overlap_prefix}\n\n{body}"
        if self._counter.count(combined) <= self.max_tokens:
            return combined
        separator_tokens = self._counter.count("\n\n")
        body_tokens = self._counter.count(body)
        overlap_budget = self.max_tokens - body_tokens - separator_tokens
        if overlap_budget <= 0:
            return body
        trimmed = self._counter.last_n_tokens(overlap_prefix, overlap_budget)
        if not trimmed:
            return body
        return f"{trimmed}\n\n{body}"

    def _pack_units(
        self,
        units: list[_SemanticUnit],
        *,
        document_name: str,
        jurisdiction: str | None,
    ) -> list[LegalChunk]:
        chunks: list[LegalChunk] = []
        buffer_parts: list[str] = []
        buffer_tokens = 0
        buffer_meta: _SemanticUnit | None = None
        buffer_clause_numbers: list[str] = []
        overlap_prefix = ""

        def finalize() -> str:
            nonlocal buffer_parts, buffer_tokens, buffer_meta, overlap_prefix
            nonlocal buffer_clause_numbers
            body = "\n\n".join(buffer_parts).strip()
            if overlap_prefix and body:
                text = self._fit_overlap(overlap_prefix, body)
            else:
                text = body or overlap_prefix
            text = text.strip()
            if not text:
                buffer_parts = []
                buffer_tokens = 0
                buffer_meta = None
                buffer_clause_numbers = []
                return ""

            token_count = self._counter.count(text)
            meta_unit = buffer_meta or units[0]
            clause_number: str | None = None
            if buffer_clause_numbers:
                clause_number = (
                    buffer_clause_numbers[0]
                    if len(buffer_clause_numbers) == 1
                    else ", ".join(buffer_clause_numbers)
                )
            chunks.append(
                LegalChunk(
                    text=text,
                    metadata=LegalChunkMetadata(
                        document_name=document_name,
                        clause_number=clause_number or meta_unit.clause_number,
                        section=meta_unit.section,
                        heading=meta_unit.heading,
                        page_number=meta_unit.page_number,
                        jurisdiction=jurisdiction,
                        chunk_index=len(chunks),
                        token_count=token_count,
                    ),
                )
            )
            overlap_prefix = self._counter.last_n_tokens(text, self.overlap_tokens)
            buffer_parts = []
            buffer_tokens = self._counter.count(overlap_prefix)
            buffer_meta = None
            buffer_clause_numbers = []
            return overlap_prefix

        for unit in units:
            unit_tokens = self._counter.count(unit.text)

            if unit_tokens > self.max_tokens:
                if buffer_parts:
                    finalize()

                for piece in self._split_oversized_text(unit.text):
                    piece_tokens = self._counter.count(piece)
                    if piece_tokens > self.max_tokens:
                        for sentence_chunk in self._split_by_sentences(
                            piece, self.max_tokens
                        ):
                            chunks.append(
                                self._make_chunk(
                                    sentence_chunk,
                                    unit,
                                    document_name,
                                    jurisdiction,
                                    len(chunks),
                                )
                            )
                    else:
                        chunks.append(
                            self._make_chunk(
                                piece,
                                unit,
                                document_name,
                                jurisdiction,
                                len(chunks),
                            )
                        )
                overlap_prefix = (
                    self._counter.last_n_tokens(chunks[-1].text, self.overlap_tokens)
                    if chunks
                    else ""
                )
                buffer_tokens = self._counter.count(overlap_prefix)
                continue

            separator_tokens = self._counter.count("\n\n") if buffer_parts else 0
            projected = buffer_tokens + separator_tokens + unit_tokens
            if overlap_prefix and not buffer_parts:
                projected = self._counter.count(
                    self._fit_overlap(overlap_prefix, unit.text)
                )
            elif overlap_prefix and buffer_parts:
                projected = self._counter.count(
                    self._fit_overlap(
                        overlap_prefix,
                        "\n\n".join([*buffer_parts, unit.text]),
                    )
                )

            if buffer_parts and projected > self.max_tokens:
                finalize()

            if not buffer_parts and overlap_prefix:
                buffer_parts = []
                buffer_tokens = self._counter.count(overlap_prefix)

            if buffer_parts:
                buffer_parts.append(unit.text)
                combined = self._assemble_chunk_text(overlap_prefix, buffer_parts)
                combined = self._truncate_to_max(combined)
                buffer_tokens = self._counter.count(combined)
                if unit.clause_number:
                    buffer_clause_numbers.append(unit.clause_number)
            else:
                if overlap_prefix:
                    buffer_parts = [unit.text]
                    combined = self._fit_overlap(overlap_prefix, unit.text)
                else:
                    buffer_parts = [unit.text]
                    combined = unit.text
                buffer_meta = unit
                if unit.clause_number:
                    buffer_clause_numbers = [unit.clause_number]
                buffer_tokens = self._counter.count(combined)

        if buffer_parts:
            finalize()

        return chunks

    def _truncate_to_max(self, text: str) -> str:
        if self._counter.count(text) <= self.max_tokens:
            return text
        return self._counter.slice_by_tokens(text, 0, self.max_tokens)

    def _make_chunk(
        self,
        text: str,
        unit: _SemanticUnit,
        document_name: str,
        jurisdiction: str | None,
        chunk_index: int,
    ) -> LegalChunk:
        return LegalChunk(
            text=text,
            metadata=LegalChunkMetadata(
                document_name=document_name,
                clause_number=unit.clause_number,
                section=unit.section,
                heading=unit.heading,
                page_number=unit.page_number,
                jurisdiction=jurisdiction,
                chunk_index=chunk_index,
                token_count=self._counter.count(text),
            ),
        )

    # ------------------------------------------------------------------
    # Splitting helpers (last resort for oversized clauses)
    # ------------------------------------------------------------------

    def _split_oversized_text(self, text: str) -> list[str]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if len(paragraphs) > 1:
            return paragraphs
        return [text]

    def _split_by_sentences(self, text: str, max_tokens: int) -> list[str]:
        sentences = SENTENCE_BOUNDARY.split(text.strip())
        if not sentences:
            return [text]

        parts: list[str] = []
        current: list[str] = []
        current_tokens = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            sent_tokens = self._counter.count(sentence)

            if sent_tokens > max_tokens:
                if current:
                    parts.append(" ".join(current))
                    current = []
                    current_tokens = 0
                parts.extend(self._hard_split(sentence, max_tokens))
                continue

            if current_tokens + sent_tokens > max_tokens and current:
                parts.append(" ".join(current))
                current = [sentence]
                current_tokens = sent_tokens
            else:
                current.append(sentence)
                current_tokens += sent_tokens

        if current:
            parts.append(" ".join(current))
        return parts or [text]

    def _hard_split(self, text: str, max_tokens: int) -> list[str]:
        """Token-level split as absolute fallback."""
        total = self._counter.total_tokens(text)
        parts: list[str] = []
        step = max(max_tokens - self.overlap_tokens, 1)
        for start in range(0, total, step):
            parts.append(self._counter.slice_by_tokens(text, start, max_tokens))
        return parts

    @staticmethod
    def _match_clause_start(text: str) -> tuple[str, str] | None:
        for pattern in CLAUSE_PATTERNS:
            match = pattern.match(text)
            if match:
                return match.group(1), match.group(2)
        return None


def infer_jurisdiction(text: str) -> str | None:
    """Best-effort jurisdiction extraction from document text."""
    sample = text[:8000]
    for pattern in JURISDICTION_PATTERNS:
        match = pattern.search(sample)
        if match:
            if match.lastindex:
                return match.group(1).strip().rstrip(".,;")
            return match.group(0).strip()
    return None


def get_legal_chunker() -> LegalDocumentChunker:
    """Factory for the configured legal document chunker."""
    return LegalDocumentChunker()


def get_text_splitter() -> SentenceSplitter:
    """Legacy sentence splitter — prefer get_legal_chunker() for legal docs."""
    return SentenceSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )

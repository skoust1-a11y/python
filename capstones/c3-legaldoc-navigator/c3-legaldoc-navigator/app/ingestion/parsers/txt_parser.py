"""Plain-text document parser."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.ingestion.extractors import StructureExtractor, TextLine
from app.ingestion.models import DocumentMetadata, ParsedDocument
from app.ingestion.protocols import BaseDocumentParser


class TxtParser(BaseDocumentParser):
    """Parse plain-text legal documents."""

    def __init__(self, extractor: StructureExtractor | None = None) -> None:
        self._extractor = extractor or StructureExtractor()

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".txt"})

    def parse(self, file_path: Path) -> ParsedDocument:
        raw_text = file_path.read_text(encoding="utf-8", errors="replace")
        lines = [
            TextLine(text=line, line_number=idx + 1)
            for idx, line in enumerate(raw_text.splitlines())
        ]

        headings = self._extractor.extract_headings(lines)
        clauses = self._extractor.extract_clauses(lines, headings)
        sections = self._extractor.build_sections(lines, headings, clauses)
        title = self._extractor.infer_title(lines, headings)

        stat = file_path.stat()
        metadata = DocumentMetadata(
            filename=file_path.name,
            file_type="txt",
            file_size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        )

        return ParsedDocument(
            title=title,
            metadata=metadata,
            sections=sections,
            headings=headings,
            clauses=clauses,
            tables=[],
            raw_text=raw_text,
        )

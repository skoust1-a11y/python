"""DOCX document parser using python-docx."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from docx import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.ingestion.extractors import StructureExtractor, TextLine
from app.ingestion.models import DocumentMetadata, Heading, ParsedDocument, TableData
from app.ingestion.protocols import BaseDocumentParser


class DocxParser(BaseDocumentParser):
    """Parse Microsoft Word documents into structured legal content."""

    HEADING_STYLE_PREFIX = "Heading"

    def __init__(self, extractor: StructureExtractor | None = None) -> None:
        self._extractor = extractor or StructureExtractor()

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".docx"})

    def parse(self, file_path: Path) -> ParsedDocument:
        document = DocxDocument(str(file_path))
        lines, docx_headings = self._extract_paragraphs(document)
        tables = self._extract_tables(document)

        headings = docx_headings or self._extractor.extract_headings(lines)
        clauses = self._extractor.extract_clauses(lines, headings)
        sections = self._extractor.build_sections(lines, headings, clauses)

        props = document.core_properties
        metadata_title = props.title
        title = self._extractor.infer_title(lines, headings, metadata_title)

        stat = file_path.stat()
        metadata = DocumentMetadata(
            filename=file_path.name,
            file_type="docx",
            file_size_bytes=stat.st_size,
            author=props.author,
            title=props.title,
            subject=props.subject,
            creator=props.last_modified_by,
            created_at=self._to_utc(props.created),
            modified_at=self._to_utc(props.modified),
        )

        raw_text = "\n".join(line.text for line in lines if line.text.strip())

        return ParsedDocument(
            title=title,
            metadata=metadata,
            sections=sections,
            headings=headings,
            clauses=clauses,
            tables=tables,
            raw_text=raw_text,
        )

    def _extract_paragraphs(
        self, document: DocxDocument
    ) -> tuple[list[TextLine], list[Heading]]:
        lines: list[TextLine] = []
        headings: list[Heading] = []
        line_number = 0

        for block in self._iter_block_items(document):
            if isinstance(block, Paragraph):
                text = block.text.strip()
                if not text:
                    continue
                line_number += 1
                level = self._heading_level_from_style(block)
                lines.append(TextLine(text=text, line_number=line_number))
                if level is not None:
                    headings.append(
                        Heading(level=level, text=text, line_number=line_number)
                    )

        return lines, headings

    def _extract_tables(self, document: DocxDocument) -> list[TableData]:
        tables: list[TableData] = []
        for idx, table in enumerate(document.tables):
            rows_data = [[cell.text.strip() for cell in row.cells] for row in table.rows]
            headers: list[str] = []
            body_rows: list[list[str]] = rows_data
            if rows_data:
                headers = rows_data[0]
                body_rows = rows_data[1:] if len(rows_data) > 1 else []
            tables.append(
                TableData(index=idx, headers=headers, rows=body_rows)
            )
        return tables

    def _heading_level_from_style(self, paragraph: Paragraph) -> int | None:
        style_name = paragraph.style.name if paragraph.style else ""
        if style_name.startswith(self.HEADING_STYLE_PREFIX):
            suffix = style_name[len(self.HEADING_STYLE_PREFIX) :]
            if suffix.isdigit():
                return int(suffix)
            return 1
        return None

    def _iter_block_items(self, document: DocxDocument):
        """Yield paragraphs and tables in document order."""
        from docx.oxml.ns import qn

        body = document.element.body
        for child in body.iterchildren():
            if child.tag == qn("w:p"):
                yield Paragraph(child, document)
            elif child.tag == qn("w:tbl"):
                yield Table(child, document)

    @staticmethod
    def _to_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

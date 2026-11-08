"""PDF document parser using PyMuPDF."""

from __future__ import annotations

from pathlib import Path

import fitz

from app.ingestion.extractors import StructureExtractor, TextLine
from app.ingestion.models import DocumentMetadata, ParsedDocument, TableData
from app.ingestion.parsers.scanned_pdf_parser import ScannedPDFParser
from app.ingestion.protocols import BaseDocumentParser, OCRServiceProtocol

# Minimum average characters per page to consider a PDF text-based
SCANNED_TEXT_THRESHOLD = 50


class PDFParser(BaseDocumentParser):
    """Parse text-based PDFs with PyMuPDF; delegates to OCR for scanned pages."""

    def __init__(
        self,
        extractor: StructureExtractor | None = None,
        scanned_parser: ScannedPDFParser | None = None,
        ocr_service: OCRServiceProtocol | None = None,
        scanned_threshold: int = SCANNED_TEXT_THRESHOLD,
    ) -> None:
        self._extractor = extractor or StructureExtractor()
        self._scanned_threshold = scanned_threshold
        self._scanned_parser = scanned_parser or ScannedPDFParser(
            ocr_service=ocr_service,
            extractor=self._extractor,
        )

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".pdf"})

    def parse(self, file_path: Path) -> ParsedDocument:
        doc = fitz.open(str(file_path))
        try:
            if self._is_scanned(doc):
                return self._scanned_parser.parse(file_path)

            lines, tables = self._extract_content(doc)
            headings = self._extractor.extract_headings(lines)
            clauses = self._extractor.extract_clauses(lines, headings)
            sections = self._extractor.build_sections(lines, headings, clauses)
            title = self._extractor.infer_title(
                lines, headings, doc.metadata.get("title")
            )
            raw_text = "\n".join(line.text for line in lines if line.text.strip())

            stat = file_path.stat()
            metadata = DocumentMetadata(
                filename=file_path.name,
                file_type="pdf",
                file_size_bytes=stat.st_size,
                page_count=len(doc),
                author=doc.metadata.get("author"),
                title=doc.metadata.get("title"),
                subject=doc.metadata.get("subject"),
                creator=doc.metadata.get("creator"),
                is_scanned=False,
                extra={"parser": "pymupdf"},
            )

            return ParsedDocument(
                title=title,
                metadata=metadata,
                sections=sections,
                headings=headings,
                clauses=clauses,
                tables=tables,
                raw_text=raw_text,
            )
        finally:
            doc.close()

    def _is_scanned(self, doc: fitz.Document) -> bool:
        if len(doc) == 0:
            return False
        total_chars = 0
        for page in doc:
            total_chars += len(page.get_text("text").strip())
        avg_chars = total_chars / len(doc)
        return avg_chars < self._scanned_threshold

    def _extract_content(
        self, doc: fitz.Document
    ) -> tuple[list[TextLine], list[TableData]]:
        lines: list[TextLine] = []
        tables: list[TableData] = []
        line_number = 0
        table_index = 0

        for page_index in range(len(doc)):
            page = doc[page_index]
            page_num = page_index + 1

            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    text = "".join(span.get("text", "") for span in spans).strip()
                    if not text:
                        continue
                    line_number += 1
                    font_size = max(
                        (span.get("size", 0) for span in spans), default=None
                    )
                    lines.append(
                        TextLine(
                            text=text,
                            page=page_num,
                            line_number=line_number,
                            font_size=font_size,
                        )
                    )

            page_tables = self._extract_page_tables(page, page_num, table_index)
            table_index += len(page_tables)
            tables.extend(page_tables)

        return lines, tables

    def _extract_page_tables(
        self, page: fitz.Page, page_num: int, start_index: int
    ) -> list[TableData]:
        tables: list[TableData] = []
        try:
            found = page.find_tables()
        except AttributeError:
            return tables

        for offset, table in enumerate(found.tables):
            rows_data = table.extract()
            if not rows_data:
                continue
            cleaned = [
                [str(cell).strip() if cell is not None else "" for cell in row]
                for row in rows_data
            ]
            headers = cleaned[0] if cleaned else []
            body = cleaned[1:] if len(cleaned) > 1 else []
            tables.append(
                TableData(
                    index=start_index + offset,
                    page=page_num,
                    headers=headers,
                    rows=body,
                )
            )
        return tables

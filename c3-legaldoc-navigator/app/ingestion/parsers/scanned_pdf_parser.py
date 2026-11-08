"""Scanned PDF parser using OCR."""

from __future__ import annotations

from pathlib import Path

import fitz

from app.ingestion.extractors import StructureExtractor, TextLine
from app.ingestion.models import DocumentMetadata, ParsedDocument
from app.ingestion.ocr import TesseractOCRService
from app.ingestion.protocols import BaseDocumentParser, OCRServiceProtocol


class ScannedPDFParser(BaseDocumentParser):
    """Extract text from scanned PDFs via page rendering and OCR."""

    DEFAULT_DPI = 300

    def __init__(
        self,
        ocr_service: OCRServiceProtocol | None = None,
        extractor: StructureExtractor | None = None,
        dpi: int = DEFAULT_DPI,
    ) -> None:
        self._ocr = ocr_service or TesseractOCRService()
        self._extractor = extractor or StructureExtractor()
        self._dpi = dpi

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".pdf"})

    def parse(self, file_path: Path) -> ParsedDocument:
        doc = fitz.open(str(file_path))
        try:
            page_texts: list[str] = []
            lines: list[TextLine] = []
            line_number = 0

            for page_index in range(len(doc)):
                page = doc[page_index]
                page_num = page_index + 1
                image_bytes = self._render_page(page)
                text = self._ocr.extract_text_from_page_image(image_bytes)
                page_texts.append(text)

                for line in text.splitlines():
                    stripped = line.strip()
                    if not stripped:
                        continue
                    line_number += 1
                    lines.append(
                        TextLine(
                            text=stripped,
                            page=page_num,
                            line_number=line_number,
                        )
                    )

            raw_text = "\n\n".join(page_texts)
            headings = self._extractor.extract_headings(lines)
            clauses = self._extractor.extract_clauses(lines, headings)
            sections = self._extractor.build_sections(lines, headings, clauses)
            title = self._extractor.infer_title(
                lines, headings, doc.metadata.get("title")
            )

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
                is_scanned=True,
                extra={"parser": "ocr", "dpi": self._dpi},
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
        finally:
            doc.close()

    def _render_page(self, page: fitz.Page) -> bytes:
        zoom = self._dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        return pixmap.tobytes("png")

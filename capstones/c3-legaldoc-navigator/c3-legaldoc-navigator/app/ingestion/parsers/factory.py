"""Factory for selecting the appropriate document parser."""

from __future__ import annotations

from pathlib import Path

from app.ingestion.parsers.docx_parser import DocxParser
from app.ingestion.parsers.pdf_parser import PDFParser
from app.ingestion.parsers.txt_parser import TxtParser
from app.ingestion.protocols import BaseDocumentParser, DocumentParserProtocol


class ParserFactory:
    """Create format-specific parsers (Open/Closed — extend via registration)."""

    def __init__(self, parsers: list[BaseDocumentParser] | None = None) -> None:
        self._parsers: list[BaseDocumentParser] = parsers or [
            PDFParser(),
            DocxParser(),
            TxtParser(),
        ]

    def register(self, parser: BaseDocumentParser) -> None:
        """Register an additional parser implementation."""
        self._parsers.insert(0, parser)

    def get_parser(self, file_path: Path) -> DocumentParserProtocol:
        suffix = file_path.suffix.lower()
        for parser in self._parsers:
            if parser.can_parse(file_path):
                return parser
        supported = sorted(
            {ext for parser in self._parsers for ext in parser.supported_extensions}
        )
        raise ValueError(
            f"Unsupported file type '{suffix}'. Supported: {', '.join(supported)}"
        )

    @property
    def supported_extensions(self) -> frozenset[str]:
        extensions: set[str] = set()
        for parser in self._parsers:
            extensions.update(parser.supported_extensions)
        return frozenset(extensions)

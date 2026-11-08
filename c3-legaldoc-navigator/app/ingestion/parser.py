"""Document parsing facade for the ingestion pipeline."""

from __future__ import annotations

from pathlib import Path

from app.ingestion.models import ParsedDocument
from app.ingestion.parsers.factory import ParserFactory
from app.ingestion.protocols import DocumentParserProtocol


class DocumentParser:
    """High-level parser that delegates to format-specific implementations."""

    def __init__(
        self,
        factory: ParserFactory | None = None,
    ) -> None:
        self._factory = factory or ParserFactory()

    @property
    def supported_extensions(self) -> frozenset[str]:
        return self._factory.supported_extensions

    def get_parser(self, file_path: Path) -> DocumentParserProtocol:
        return self._factory.get_parser(file_path)

    def parse(self, file_path: Path) -> ParsedDocument:
        parser = self._factory.get_parser(file_path)
        return parser.parse(file_path)

    def parse_to_json(self, file_path: Path, *, indent: int = 2) -> str:
        return self.parse(file_path).to_json(indent=indent)

"""LlamaIndex reader integration for legal document parsing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document

from app.ingestion.models import ParsedDocument
from app.ingestion.parsers.factory import ParserFactory
from app.ingestion.protocols import DocumentParserProtocol


class LegalDocumentReader(BaseReader):
    """LlamaIndex reader that produces Documents from structured legal parsers."""

    def __init__(
        self,
        parser_factory: ParserFactory | None = None,
    ) -> None:
        self._factory = parser_factory or ParserFactory()
        self._last_parsed: ParsedDocument | None = None

    @property
    def last_parsed(self) -> ParsedDocument | None:
        """Most recently parsed document (available after load_data)."""
        return self._last_parsed

    def load_data(
        self,
        file_path: str | Path,
        extra_info: dict[str, Any] | None = None,
    ) -> list[Document]:
        path = Path(file_path)
        parser = self._factory.get_parser(path)
        parsed = self._parse(path, parser)
        self._last_parsed = parsed

        metadata = parsed.to_dict()
        metadata.pop("raw_text", None)
        if extra_info:
            metadata.update(extra_info)

        return [
            Document(
                text=parsed.raw_text,
                metadata=metadata,
            )
        ]

    def _parse(
        self, path: Path, parser: DocumentParserProtocol
    ) -> ParsedDocument:
        return parser.parse(path)

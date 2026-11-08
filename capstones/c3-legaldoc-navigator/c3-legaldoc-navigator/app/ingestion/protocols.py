"""Abstract interfaces for the ingestion pipeline (Dependency Inversion)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.ingestion.models import ParsedDocument


@runtime_checkable
class DocumentParserProtocol(Protocol):
    """Interface that all format-specific parsers must satisfy."""

    @property
    def supported_extensions(self) -> frozenset[str]:
        """File extensions this parser handles (e.g. {'.pdf'})."""
        ...

    def can_parse(self, file_path: Path) -> bool:
        """Return True when this parser can handle the given file."""
        ...

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse the file and return a structured document."""
        ...


@runtime_checkable
class OCRServiceProtocol(Protocol):
    """Interface for OCR backends used on scanned documents."""

    def extract_text_from_page_image(self, image_bytes: bytes) -> str:
        """Run OCR on a single page image and return extracted text."""
        ...


class BaseDocumentParser(ABC):
    """Abstract base class providing common parser behaviour."""

    @property
    @abstractmethod
    def supported_extensions(self) -> frozenset[str]:
        raise NotImplementedError

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.supported_extensions

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        raise NotImplementedError

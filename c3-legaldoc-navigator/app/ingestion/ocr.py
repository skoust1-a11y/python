"""OCR service implementations for scanned document processing."""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)


class TesseractOCRService:
    """OCR backend using Tesseract via pytesseract."""

    def __init__(self, lang: str = "eng") -> None:
        self._lang = lang

    def extract_text_from_page_image(self, image_bytes: bytes) -> str:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError(
                "pytesseract and Pillow are required for OCR. "
                "Install with: pip install pytesseract Pillow"
            ) from exc

        image = Image.open(io.BytesIO(image_bytes))
        try:
            return pytesseract.image_to_string(image, lang=self._lang)
        except pytesseract.TesseractNotFoundError as exc:
            logger.error("Tesseract binary not found on PATH")
            raise RuntimeError(
                "Tesseract OCR engine is not installed. "
                "Install from https://github.com/tesseract-ocr/tesseract"
            ) from exc

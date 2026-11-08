"""Structured logging configuration."""

import logging

from app.core.config import settings


_HTTP_DEBUG_LOGGERS = ("httpx", "groq", "openai", "llama_index")


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    for logger_name in _HTTP_DEBUG_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.DEBUG)

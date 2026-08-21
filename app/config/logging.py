"""Process-wide logging configuration."""

from __future__ import annotations

import logging
from logging.config import dictConfig

from app.config.settings import Settings

LOGGABLE_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def configure_logging(settings: Settings) -> None:
    """Configure stdout logging from `LOG_LEVEL`. Safe to call more than once."""
    level = settings.log_level.upper()
    if level not in LOGGABLE_LEVELS:
        level = "INFO"

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {"level": level, "handlers": ["console"]},
            "loggers": {
                "app": {"level": level, "propagate": True},
            },
        }
    )
    logging.getLogger("app").debug("Logging configured at %s", level)
    # Vendor HTTP clients can echo Authorization headers at DEBUG.
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("google_genai").setLevel(logging.WARNING)
    logging.getLogger("google.genai").setLevel(logging.WARNING)

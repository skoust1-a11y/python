"""Process-wide logging configuration."""

from __future__ import annotations

import logging
from logging.config import dictConfig

from pathlib import Path

from app.config.settings import Settings

LOGGABLE_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def configure_logging(settings: Settings) -> None:
    """Configure stdout and structured category-specific rotating log files."""
    level = settings.log_level.upper()
    if level not in LOGGABLE_LEVELS:
        level = "INFO"

    formatter_config = {
        "default": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)-22s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    }

    handlers: dict[str, dict[str, object]] = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        }
    }
    root_handlers = ["console"]
    logger_configs: dict[str, dict[str, object]] = {
        "app": {"level": level, "propagate": True},
    }

    log_file = (settings.log_file or "").strip()
    if log_file:
        file_path = Path(log_file)
        log_dir = file_path.parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # 1. Main Unified Log File
        handlers["file_app"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": str(file_path),
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "encoding": "utf-8",
        }
        root_handlers.append("file_app")

        # 2. Errors & Warnings Dedicated Log File
        handlers["file_errors"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": str(log_dir / "errors.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
            "level": "WARNING",
        }
        root_handlers.append("file_errors")

        # 3. LangGraph Workflow Dedicated Log File
        handlers["file_workflow"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": str(log_dir / "workflow.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        }
        logger_configs["app.workflow"] = {
            "level": level,
            "handlers": ["file_workflow"],
            "propagate": True,
        }

        # 4. Specialist Agents Logs (Combined & Agent-Specific Subfolder)
        handlers["file_agents"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": str(log_dir / "agents.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        }
        logger_configs["app.agents"] = {
            "level": level,
            "handlers": ["file_agents"],
            "propagate": True,
        }

        # Dedicated Agent Subdirectory
        agents_dir = log_dir / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        agent_log_map = {
            "app.agents.portfolio_manager": "manager.log",
            "app.agents.market_analysis": "market.log",
            "app.agents.fundamental_analysis": "fundamental.log",
            "app.agents.risk_assessment": "risk.log",
            "app.agents.portfolio_optimization": "optimization.log",
        }

        for logger_name, log_filename in agent_log_map.items():
            handler_key = f"file_agent_{log_filename.replace('.log', '')}"
            handlers[handler_key] = {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "filename": str(agents_dir / log_filename),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
            }
            logger_configs[logger_name] = {
                "level": level,
                "handlers": [handler_key],
                "propagate": True,
            }

        # 5. External Providers Dedicated Log File
        handlers["file_providers"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": str(log_dir / "providers.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        }
        logger_configs["app.providers"] = {
            "level": level,
            "handlers": ["file_providers"],
            "propagate": True,
        }

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": formatter_config,
            "handlers": handlers,
            "root": {"level": level, "handlers": root_handlers},
            "loggers": logger_configs,
        }
    )
    logging.getLogger("app").debug("Logging configured at %s (file=%s)", level, log_file or "disabled")
    # Vendor HTTP clients can echo Authorization headers at DEBUG.
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("google_genai").setLevel(logging.WARNING)
    logging.getLogger("google.genai").setLevel(logging.WARNING)
    logging.getLogger("langfuse").setLevel(logging.WARNING)

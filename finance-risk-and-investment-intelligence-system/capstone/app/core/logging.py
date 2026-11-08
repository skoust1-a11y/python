from __future__ import annotations

import logging
from pathlib import Path

import structlog

from app.core.config import get_settings

_LEVELS = ("debug", "info", "warning", "error")
_AGENTS = (
    "api",
    "graph",
    "input_guard",
    "router",
    "retrieval",
    "portfolio_eval",
    "market_data",
    "risk",
    "escalation",
    "synthesis",
)
_configured = False
_agent_files: set[str] = set()


class _ExactLevel(logging.Filter):
    def __init__(self, level: int):
        super().__init__()
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == self.level


def log_dir() -> Path:
    path = Path(get_settings().log_dir)
    return path if path.is_absolute() else Path(__file__).resolve().parents[2] / path


def bind_log(**fields) -> None:
    structlog.contextvars.bind_contextvars(**fields)


def clear_log() -> None:
    structlog.contextvars.clear_contextvars()


def reset_logging() -> None:
    global _configured
    for name in list(_agent_files):
        logging.getLogger("frii.{}".format(name)).handlers.clear()
    logging.getLogger("frii").handlers.clear()
    _agent_files.clear()
    _configured = False


def _formatter() -> logging.Formatter:
    return structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )


def _file(path: Path, level: int, exact: int | None = None) -> logging.Handler:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return logging.NullHandler()
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(_formatter())
    if exact is not None:
        handler.addFilter(_ExactLevel(exact))
    return handler


def _attach_agent(name: str, level: int) -> None:
    if name in _agent_files:
        return
    logger = logging.getLogger("frii.{}".format(name))
    logger.setLevel(level)
    logger.propagate = True
    logger.addHandler(_file(log_dir() / "agents" / "{}.log".format(name), level))
    _agent_files.add(name)


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = log_dir()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    base = logging.getLogger("frii")
    base.handlers.clear()
    base.setLevel(level)
    base.propagate = False
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(_formatter())
    base.addHandler(console)
    base.addHandler(_file(root / "app.log", level))
    for name in _LEVELS:
        num = getattr(logging, name.upper())
        base.addHandler(_file(root / "levels" / "{}.log".format(name), num, exact=num))
    for agent in _AGENTS:
        _attach_agent(agent, level)
    _configured = True


def get_logger(name: str = "graph"):
    if _configured:
        _attach_agent(name, getattr(logging, get_settings().log_level.upper(), logging.INFO))
    return structlog.get_logger("frii.{}".format(name))

import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger, log_dir, reset_logging


def test_logs_split_by_level_and_agent(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    try:
        get_settings.cache_clear()
        reset_logging()
        configure_logging()

        get_logger("router").debug("pick", query_id="portfolios.all_in_scope")
        get_logger("router").info("agent", agent="router")
        get_logger("retrieval").error("failed", agent="retrieval")

        root = Path(log_dir())
        for name in ("frii", "frii.router", "frii.retrieval"):
            for handler in logging.getLogger(name).handlers:
                handler.flush()

        router = (root / "agents" / "router.log").read_text()
        retrieval = (root / "agents" / "retrieval.log").read_text()
        info = (root / "levels" / "info.log").read_text()
        error = (root / "levels" / "error.log").read_text()
        debug = (root / "levels" / "debug.log").read_text()
        app = (root / "app.log").read_text()

        assert '"agent": "router"' in router
        assert "pick" in router
        assert "failed" not in router
        assert "failed" in retrieval
        assert '"agent": "router"' not in retrieval
        assert "pick" in debug and "failed" not in debug
        assert '"agent": "router"' in info and "failed" not in info
        assert "failed" in error and "pick" not in error
        assert "pick" in app and "failed" in app
    finally:
        reset_logging()
        monkeypatch.delenv("LOG_DIR", raising=False)
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        get_settings.cache_clear()
        configure_logging()

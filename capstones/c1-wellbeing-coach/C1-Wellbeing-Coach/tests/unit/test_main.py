"""Unit tests for app.main module."""

import asyncio
from unittest.mock import patch

from app.main import health_check, read_root, shutdown_event, startup_event


class TestMainModule:
    """Tests for root/health endpoints and app lifecycle events."""

    def test_read_root(self):
        result = read_root()
        assert result["message"] == "Welcome to Wellbeing Coach API"
        assert result["version"] == "1.0.0"

    def test_health_check(self):
        result = health_check()
        assert result == {"status": "healthy", "service": "wellbeing-coach"}

    @patch("app.main.initialize_database")
    def test_startup_event_calls_initialize_database(self, mock_initialize_database):
        asyncio.run(startup_event())
        mock_initialize_database.assert_called_once()

    def test_shutdown_event_runs(self):
        # Should complete without errors
        asyncio.run(shutdown_event())

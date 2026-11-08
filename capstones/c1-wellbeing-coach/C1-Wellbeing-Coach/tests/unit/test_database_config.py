"""Unit tests for database configuration helpers."""

from unittest.mock import MagicMock, patch

import pytest

from app.config.database import DatabaseConfig


class TestDatabaseConfig:
    """Tests for URL creation and initialization behavior."""

    def test_build_database_url_from_database_url_env(self):
        cfg = DatabaseConfig()
        with patch.dict(
            "os.environ",
            {"DATABASE_URL": "postgresql+psycopg://u:p@localhost:5432/db"},
            clear=True,
        ):
            assert cfg._build_database_url() == "postgresql+psycopg://u:p@localhost:5432/db"

    def test_build_database_url_from_components(self):
        cfg = DatabaseConfig()
        with patch.dict(
            "os.environ",
            {
                "DB_USER": "user1",
                "DB_PASSWORD": "pass1",
                "DB_HOST": "db.local",
                "DB_PORT": "5433",
                "DB_NAME": "wellbeing",
            },
            clear=True,
        ):
            assert (
                cfg._build_database_url()
                == "postgresql+psycopg://user1:pass1@db.local:5433/wellbeing"
            )

    def test_build_database_url_missing_required_values_raises(self):
        cfg = DatabaseConfig()
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Postgres configuration is missing"):
                cfg._build_database_url()

    def test_get_database_url_is_cached(self):
        cfg = DatabaseConfig()
        with patch.object(cfg, "_build_database_url", return_value="url1") as mock_builder:
            first = cfg.get_database_url()
            second = cfg.get_database_url()

        assert first == "url1"
        assert second == "url1"
        mock_builder.assert_called_once()

    def test_initialize_database_success_sets_initialized(self):
        cfg = DatabaseConfig()

        with patch.object(cfg, "get_engine", return_value=MagicMock()):
            with patch("app.config.database.Base.metadata.create_all") as mock_create_all:
                cfg.initialize_database()

        assert cfg._initialized is True
        mock_create_all.assert_called_once()

    def test_initialize_database_skips_when_already_initialized(self):
        cfg = DatabaseConfig()
        cfg._initialized = True

        with patch("app.config.database.Base.metadata.create_all") as mock_create_all:
            cfg.initialize_database()

        mock_create_all.assert_not_called()

    def test_initialize_database_reraises_on_failure(self):
        cfg = DatabaseConfig()
        with patch.object(cfg, "get_engine", return_value=MagicMock()):
            with patch(
                "app.config.database.Base.metadata.create_all",
                side_effect=Exception("db init failed"),
            ):
                with pytest.raises(Exception, match="db init failed"):
                    cfg.initialize_database()

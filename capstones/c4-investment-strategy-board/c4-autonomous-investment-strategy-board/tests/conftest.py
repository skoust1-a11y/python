"""Shared test fixtures."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.config.settings import Settings
from app.main import create_app
from tests.helpers import make_settings


@pytest.fixture
def settings() -> Settings:
    return make_settings(app_env="test", log_level="WARNING")


@pytest.fixture
def client(settings: Settings) -> Generator[TestClient, None, None]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client

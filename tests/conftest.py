from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> Generator[None, None, None]:
    storage = getattr(app.state.limiter, "_storage", None)

    if storage and hasattr(storage, "reset"):
        storage.reset()

    yield

    if storage and hasattr(storage, "reset"):
        storage.reset()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def concept_payload() -> dict[str, str]:
    return {
        "concept": "Photosynthesis",
        "learning_level": "beginner",
        "context": "Use a sports analogy.",
    }
"""API client fixtures for integration tests."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def client():
    """Create FastAPI test client with isolated database sessions."""
    from app.config.database import SessionLocal
    from app.main import app

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    return TestClient(app)

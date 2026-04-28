import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def api_client():
    return TestClient(app)


@pytest.fixture
def disable_rate_limit():
    app.state.limiter.enabled = False
    yield
    app.state.limiter.enabled = True
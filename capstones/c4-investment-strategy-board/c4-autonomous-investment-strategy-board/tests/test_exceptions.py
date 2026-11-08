from fastapi.testclient import TestClient

from app.exceptions import ConfigurationError
from app.main import create_app
from tests.helpers import make_settings


def test_app_error_returns_structured_json() -> None:
    application = create_app(make_settings(app_env="production"))

    @application.get("/_boom")
    def boom() -> None:
        raise ConfigurationError("missing configuration")

    client = TestClient(application, raise_server_exceptions=False)
    response = client.get("/_boom")
    assert response.status_code == 500
    body = response.json()["error"]
    assert body["code"] == "configuration_error"
    assert body["message"] == "missing configuration"


def test_unexpected_error_hides_detail_outside_development() -> None:
    application = create_app(make_settings(app_env="production"))

    @application.get("/_crash")
    def crash() -> None:
        raise RuntimeError("internal secret")

    client = TestClient(application, raise_server_exceptions=False)
    response = client.get("/_crash")
    assert response.status_code == 500
    body = response.json()["error"]
    assert body["code"] == "internal_error"
    assert "internal secret" not in response.text

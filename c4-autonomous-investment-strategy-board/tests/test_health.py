from fastapi.testclient import TestClient


def test_health_endpoint_reports_stub_providers(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["providers"] == {
        "llm": "stub",
        "market_data": "stub",
        "fundamental_data": "stub",
        "news": "stub",
    }
    serialized = response.text.lower()
    assert "api_key" not in serialized
    assert "secret" not in serialized


def test_root_endpoint(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["health"] == "/health"

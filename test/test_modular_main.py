import pytest
from fastapi.testclient import TestClient
from app.modular_main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "name" in response.json()
    assert "version" in response.json()

def test_explain_route(monkeypatch):
    class DummyService:
        def get_explanation(self, concept):
            return "dummy explanation"
    monkeypatch.setattr(app, "llm_service", DummyService())
    payload = {"concept": "test concept"}
    response = client.post("/explain", json=payload)
    assert response.status_code == 200
    assert response.json()["explanation"] == "dummy explanation"

def test_explain_stream_route(monkeypatch):
    class DummyStream:
        def __iter__(self):
            yield type("Chunk", (), {"choices": [type("Delta", (), {"delta": type("Content", (), {"content": "chunk"})()})]})()
    class DummyService:
        def get_explanation_stream(self, concept):
            return DummyStream()
    monkeypatch.setattr(app, "llm_service", DummyService())
    payload = {"concept": "test concept"}
    response = client.post("/explain/stream", json=payload, stream=True)
    assert response.status_code == 200
    assert b"chunk" in next(response.iter_bytes())

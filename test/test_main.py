import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "AI Tutor API"
    assert "version" in data
    assert "endpoints" in data

def test_explain_success(monkeypatch):
    class DummyResponse:
        choices = [type("msg", (), {"message": type("msg2", (), {"content": "explanation"})()})()]
    def dummy_create(*args, **kwargs):
        return DummyResponse()
    monkeypatch.setattr(app, "CLOUD_CLIENT", type("DummyClient", (), {"chat": type("Chat", (), {"completions": type("Completions", (), {"create": staticmethod(dummy_create)})()})()})())
    monkeypatch.setattr("app.main.insert_query_record", lambda user_query, llm_response: None)
    payload = {"concept": "test concept"}
    response = client.post("/explain", json=payload)
    assert response.status_code == 200
    assert response.json()["explanation"] == "explanation"

def test_explain_db_error(monkeypatch):
    class DummyResponse:
        choices = [type("msg", (), {"message": type("msg2", (), {"content": "explanation"})()})()]
    def dummy_create(*args, **kwargs):
        return DummyResponse()
    monkeypatch.setattr(app, "CLOUD_CLIENT", type("DummyClient", (), {"chat": type("Chat", (), {"completions": type("Completions", (), {"create": staticmethod(dummy_create)})()})()})())
    def raise_db(*args, **kwargs):
        raise Exception("DB error")
    monkeypatch.setattr("app.main.insert_query_record", raise_db)
    payload = {"concept": "test concept"}
    response = client.post("/explain", json=payload)
    assert response.status_code == 200
    assert response.json()["explanation"] == "explanation"

def test_explain_api_error(monkeypatch):
    def raise_api(*args, **kwargs):
        from openai import APIError
        raise APIError("API error")
    monkeypatch.setattr(app, "CLOUD_CLIENT", type("DummyClient", (), {"chat": type("Chat", (), {"completions": type("Completions", (), {"create": staticmethod(raise_api)})()})()})())
    payload = {"concept": "test concept"}
    response = client.post("/explain", json=payload)
    assert response.status_code == 500
    assert response.json()["detail"]["error"] == "API Error"

def test_explain_internal_error(monkeypatch):
    def raise_internal(*args, **kwargs):
        raise Exception("Internal error")
    monkeypatch.setattr(app, "CLOUD_CLIENT", type("DummyClient", (), {"chat": type("Chat", (), {"completions": type("Completions", (), {"create": staticmethod(raise_internal)})()})()})())
    payload = {"concept": "test concept"}
    response = client.post("/explain", json=payload)
    assert response.status_code == 500
    assert response.json()["detail"]["error"] == "Internal Error"

def test_explain_stream_success(monkeypatch):
    class DummyChunk:
        choices = [type("Delta", (), {"delta": type("Content", (), {"content": "chunk"})()})]
    def dummy_stream(*args, **kwargs):
        return [DummyChunk()]
    monkeypatch.setattr(app, "CLOUD_CLIENT", type("DummyClient", (), {"chat": type("Chat", (), {"completions": type("Completions", (), {"create": staticmethod(dummy_stream)})()})()})())
    payload = {"concept": "test concept"}
    response = client.post("/explain/stream", json=payload, stream=True)
    assert response.status_code == 200
    assert b"chunk" in next(response.iter_bytes())

def test_explain_stream_api_error(monkeypatch):
    def raise_api(*args, **kwargs):
        from openai import APIError
        raise APIError("API error")
    monkeypatch.setattr(app, "CLOUD_CLIENT", type("DummyClient", (), {"chat": type("Chat", (), {"completions": type("Completions", (), {"create": staticmethod(raise_api)})()})()})())
    payload = {"concept": "test concept"}
    response = client.post("/explain/stream", json=payload, stream=True)
    assert response.status_code == 200
    assert b"API error" in next(response.iter_bytes())

def test_explain_stream_internal_error(monkeypatch):
    def raise_internal(*args, **kwargs):
        raise Exception("Internal error")
    monkeypatch.setattr(app, "CLOUD_CLIENT", type("DummyClient", (), {"chat": type("Chat", (), {"completions": type("Completions", (), {"create": staticmethod(raise_internal)})()})()})())
    payload = {"concept": "test concept"}
    response = client.post("/explain/stream", json=payload, stream=True)
    assert response.status_code == 200
    assert b"Internal error" in next(response.iter_bytes())

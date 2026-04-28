from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.main as main


class FakeCompletions:
    def __init__(self, content: str = "Mocked explanation"):
        self.content = content

    def create(self, model, messages, stream=False):
        if stream:
            return [
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Part 1 "))]),
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Part 2"))]),
            ]
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class FakeChat:
    def __init__(self, content: str = "Mocked explanation"):
        self.completions = FakeCompletions(content)


class FakeClient:
    def __init__(self, content: str = "Mocked explanation"):
        self.chat = FakeChat(content)


def test_root_endpoint_returns_metadata():
    client = TestClient(main.app)
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "AI Tutor API"
    assert "explain" in body["endpoints"]


def test_explain_endpoint_returns_generated_text(monkeypatch):
    monkeypatch.setattr(main, "CLOUD_CLIENT", FakeClient("Explains RAG clearly."))
    monkeypatch.setattr(main, "insert_query_record", lambda **_: 1)

    client = TestClient(main.app)
    response = client.post("/explain", json={"concept": "RAG"})

    assert response.status_code == 200
    body = response.json()
    assert body["concept"] == "RAG"
    assert body["explanation"] == "Explains RAG clearly."
    assert body["model"] == main.CLOUD_MODEL


def test_explain_stream_returns_sse_content(monkeypatch):
    monkeypatch.setattr(main, "CLOUD_CLIENT", FakeClient("unused"))
    monkeypatch.setattr(main, "insert_query_record", lambda **_: 1)

    client = TestClient(main.app)
    response = client.post("/explain/stream", json={"concept": "RAG"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    text = response.text
    assert '"type": "metadata"' in text
    assert '"type": "content"' in text
    assert '"type": "done"' in text

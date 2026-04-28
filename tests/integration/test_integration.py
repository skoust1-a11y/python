from collections.abc import AsyncGenerator

import pytest
from fastapi import HTTPException, status

from app import main


pytestmark = pytest.mark.integration


def test_explain_endpoint_returns_expected_payload(client, concept_payload, monkeypatch) -> None:
	async def fake_explain(concept: str, learning_level: str, context: str | None = None) -> str:
		assert concept == concept_payload["concept"]
		assert learning_level == concept_payload["learning_level"]
		assert context == concept_payload["context"]
		return "Plants convert sunlight into usable energy"

	monkeypatch.setattr(main.tutor, "explain_with_cloud_model", fake_explain)

	response = client.post("/explain", json=concept_payload)

	assert response.status_code == status.HTTP_200_OK
	body = response.json()
	assert body["concept"] == concept_payload["concept"]
	assert body["learning_level"] == concept_payload["learning_level"]
	assert body["model_used"] == main.CLOUD_MODEL
	assert body["tokens_used"] == 6


def test_explain_endpoint_returns_assignment_style_validation_error(client) -> None:
	response = client.post(
		"/explain",
		json={"concept": "", "learning_level": "expert", "context": "short"},
	)

	assert response.status_code == status.HTTP_400_BAD_REQUEST
	body = response.json()
	assert body["error"] == "ValidationError"
	assert body["status_code"] == status.HTTP_400_BAD_REQUEST
	assert "learning_level" in body["detail"] or "concept" in body["detail"]


def test_personalize_endpoint_surfaces_service_errors(client, concept_payload, monkeypatch) -> None:
	async def fake_personalize(concept: str, context: str | None = None) -> str:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Ollama is unavailable",
		)

	monkeypatch.setattr(main.tutor, "personalize_with_local_model", fake_personalize)

	response = client.post("/personalize", json=concept_payload)

	assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
	body = response.json()
	assert body["error"] == "Service Unavailable"
	assert body["detail"] == "Ollama is unavailable"


def test_explain_endpoint_returns_500_for_unexpected_errors(client, concept_payload, monkeypatch) -> None:
	async def broken_explain(concept: str, learning_level: str, context: str | None = None) -> str:
		raise RuntimeError("cloud failure")

	monkeypatch.setattr(main.tutor, "explain_with_cloud_model", broken_explain)

	response = client.post("/explain", json=concept_payload)

	assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
	body = response.json()
	assert body["error"] == "Internal Server Error"
	assert "cloud failure" in body["detail"]


def test_personalize_endpoint_returns_500_for_unexpected_errors(client, concept_payload, monkeypatch) -> None:
	async def broken_personalize(concept: str, context: str | None = None) -> str:
		raise RuntimeError("local failure")

	monkeypatch.setattr(main.tutor, "personalize_with_local_model", broken_personalize)

	response = client.post("/personalize", json=concept_payload)

	assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
	body = response.json()
	assert body["error"] == "Internal Server Error"
	assert "local failure" in body["detail"]


def test_stream_endpoint_returns_sse_chunks(client, concept_payload, monkeypatch) -> None:
	async def fake_stream(
		concept: str,
		learning_level: str,
		context: str | None = None,
	) -> AsyncGenerator[str, None]:
		yield 'data: {"chunk":"first","chunk_index":0,"is_complete":false}\n\n'
		yield 'event: done\ndata: {"chunk":"","chunk_index":1,"is_complete":true}\n\n'

	monkeypatch.setattr(main.tutor, "stream_explanation", fake_stream)

	with client.stream("POST", "/explain/stream", json=concept_payload) as response:
		body = "".join(response.iter_text())

	assert response.status_code == status.HTTP_200_OK
	assert response.headers["content-type"].startswith("text/event-stream")
	assert "data:" in body
	assert "event: done" in body


def test_stream_endpoint_returns_500_for_unexpected_errors(client, concept_payload, monkeypatch) -> None:
	def broken_stream(concept: str, learning_level: str, context: str | None = None):
		raise RuntimeError("stream failure")

	monkeypatch.setattr(main.tutor, "stream_explanation", broken_stream)

	response = client.post("/explain/stream", json=concept_payload)

	assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
	body = response.json()
	assert body["error"] == "Internal Server Error"
	assert "stream failure" in body["detail"]


def test_explain_endpoint_enforces_rate_limit(client, concept_payload, monkeypatch) -> None:
	async def fake_explain(concept: str, learning_level: str, context: str | None = None) -> str:
		return "short answer"

	monkeypatch.setattr(main.tutor, "explain_with_cloud_model", fake_explain)

	for _ in range(3):
		response = client.post("/explain", json=concept_payload)
		assert response.status_code == status.HTTP_200_OK

	response = client.post("/explain", json=concept_payload)

	assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
	body = response.json()
	assert body["error"] == "RateLimitExceeded"
	assert body["status_code"] == status.HTTP_429_TOO_MANY_REQUESTS
	assert body["retry_after"] == 60

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
import requests
from fastapi import HTTPException, status

from app.main import TutorAI


pytestmark = pytest.mark.unit


def test_explain_with_cloud_model_returns_trimmed_content() -> None:
	service = TutorAI()
	create_completion = AsyncMock(
		return_value=SimpleNamespace(
			choices=[SimpleNamespace(message=SimpleNamespace(content="  Clear answer  "))]
		)
	)
	service.cloud_model = "test-cloud-model"
	service.cloud_client = SimpleNamespace(
		chat=SimpleNamespace(
			completions=SimpleNamespace(create=create_completion),
		)
	)

	result = asyncio.run(
		service.explain_with_cloud_model(
			concept="Recursion",
			learning_level="beginner",
			context="Use short examples",
		)
	)

	assert result == "Clear answer"
	assert create_completion.await_count == 1
	request_kwargs = create_completion.await_args.kwargs
	assert request_kwargs["model"] == "test-cloud-model"
	assert "Learner context: Use short examples" in request_kwargs["messages"][1]["content"]


def test_explain_with_cloud_model_raises_unauthorized_without_client() -> None:
	service = TutorAI()
	service.cloud_client = None

	with pytest.raises(HTTPException) as exc_info:
		asyncio.run(service.explain_with_cloud_model("Recursion", "beginner"))

	assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
	assert "OPENAI_API_KEY" in exc_info.value.detail


def test_personalize_with_local_model_returns_trimmed_content() -> None:
	service = TutorAI()
	service.ollama_url = "http://localhost:11434"
	service.ollama_model = "llama3"

	response = Mock(status_code=200)
	response.json.return_value = {"response": "  Personalized answer  "}

	with patch.object(service, "_validate_ollama_connection", return_value=True):
		with patch("app.main.requests.post", return_value=response) as post_mock:
			result = asyncio.run(
				service.personalize_with_local_model(
					concept="Binary Search",
					context="I like game examples",
				)
			)

	assert result == "Personalized answer"
	assert post_mock.call_count == 1
	request_json = post_mock.call_args.kwargs["json"]
	assert request_json["model"] == "llama3"
	assert request_json["stream"] is False


def test_personalize_with_local_model_raises_timeout() -> None:
	service = TutorAI()
	service.ollama_url = "http://localhost:11434"
	service.ollama_model = "llama3"

	with patch.object(service, "_validate_ollama_connection", return_value=True):
		with patch("app.main.requests.post", side_effect=requests.exceptions.Timeout):
			with pytest.raises(HTTPException) as exc_info:
				asyncio.run(service.personalize_with_local_model("Sorting"))

	assert exc_info.value.status_code == status.HTTP_504_GATEWAY_TIMEOUT
	assert "timed out" in exc_info.value.detail.lower()


def test_stream_explanation_yields_sse_chunks_and_done_event() -> None:
	service = TutorAI()
	service.cloud_client = object()
	service.explain_with_cloud_model = AsyncMock(return_value="alpha beta")

	async def collect_chunks() -> list[str]:
		with patch("app.main.asyncio.sleep", new=AsyncMock()):
			return [chunk async for chunk in service.stream_explanation("Trees", "beginner")]

	chunks = asyncio.run(collect_chunks())

	assert chunks[0].startswith("data: ")
	assert '"chunk":"alpha"' in chunks[0]
	assert '"chunk":"beta"' in chunks[1]
	assert chunks[-1].startswith("event: done")

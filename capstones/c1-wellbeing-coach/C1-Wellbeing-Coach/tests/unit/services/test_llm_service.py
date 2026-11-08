"""Unit tests for LLMService (mocked, no real network calls)."""

import os
from unittest.mock import MagicMock, patch

import pytest
from httpx import ConnectError
from openai import OpenAIError

from app.services.llm_service import call_gemini_llm, call_gemma_llm, prompt_generate


class TestLLMService:
    """Tests for LLMService request formatting and response handling."""

    def test_prompt_generate_structure(self):
        messages = prompt_generate("hello")
        assert isinstance(messages, list)
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "hello"

    @patch("app.services.llm_service.OpenAI")
    def test_call_gemini_llm_success(self, mock_openai):

        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="gemini ok"))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "k",
            "OPENAI_BASE_URL": "https://example.com/v1",
            "OPENAI_MODEL": "gemini-model",
        }, clear=True):
            result = call_gemini_llm("test prompt")

        assert result == "gemini ok"
        mock_client.chat.completions.create.assert_called_once()

    @patch("app.services.llm_service.OpenAI")
    def test_call_gemma_llm_success(self, mock_openai):

        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="gemma ok"))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict(os.environ, {
            "OLLAMA_API_KEY": "k",
            "OLLAMA_MODEL": "gemma-model",
            "OLLAMA_BASE_URL": "http://localhost:11434/v1",
        }, clear=True):
            result = call_gemma_llm("test prompt")

        assert result == "gemma ok"
        mock_client.chat.completions.create.assert_called_once()

    @patch("app.services.llm_service.OpenAI")
    def test_call_gemini_llm_missing_env_raises_runtime_error(self, mock_openai):

        with patch.dict(os.environ, {
            "OPENAI_BASE_URL": "https://example.com/v1",
            "OPENAI_MODEL": "gemini-model",
        }, clear=True):
            try:
                call_gemini_llm("test prompt")
                assert False, "Expected RuntimeError"
            except RuntimeError as exc:
                assert "Env config missing error" in str(exc)

        mock_openai.assert_not_called()

    @patch("app.services.llm_service.OpenAI")
    def test_call_gemma_llm_missing_env_raises_runtime_error(self, mock_openai):

        with patch.dict(os.environ, {
            "OLLAMA_MODEL": "gemma-model",
            "OLLAMA_BASE_URL": "http://localhost:11434/v1",
        }, clear=True):
            try:
                call_gemma_llm("test prompt")
                assert False, "Expected RuntimeError"
            except RuntimeError as exc:
                assert "Env config missing error" in str(exc)

        mock_openai.assert_not_called()

    @patch("app.services.llm_service.OpenAI")
    def test_call_gemini_llm_connect_error_is_raised(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = ConnectError("down")

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "k",
            "OPENAI_BASE_URL": "https://example.com/v1",
            "OPENAI_MODEL": "gemini-model",
        }, clear=True):
            with pytest.raises(ConnectError):
                call_gemini_llm("test prompt")

    @patch("app.services.llm_service.OpenAI")
    def test_call_gemma_llm_openai_error_is_raised(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = OpenAIError("sdk err")

        with patch.dict(os.environ, {
            "OLLAMA_API_KEY": "k",
            "OLLAMA_MODEL": "gemma-model",
            "OLLAMA_BASE_URL": "http://localhost:11434/v1",
        }, clear=True):
            with pytest.raises(OpenAIError, match="OPENAI SDK ERROR"):
                call_gemma_llm("test prompt")

    @patch("app.services.llm_service.OpenAI", side_effect=Exception("unexpected"))
    def test_call_gemini_llm_generic_exception_is_wrapped(self, mock_openai):
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "k",
            "OPENAI_BASE_URL": "https://example.com/v1",
            "OPENAI_MODEL": "gemini-model",
        }, clear=True):
            with pytest.raises(Exception, match="ERROR"):
                call_gemini_llm("test prompt")

import pytest
from app.main import validate_env, build_messages,call_openai
import pytest
from openai import OpenAIError
# import httpx
import os
import pytest
from unittest.mock import patch, MagicMock
from openai import OpenAIError
import httpx
from app.main import stream_response_func

# -------------------------------
# validate_env tests
# -------------------------------
@pytest.mark.unit
def test_validate_env_success():
    # Should not raise an exception
    validate_env("key", "url", "model")


@pytest.mark.unit
def test_validate_env_failure_missing_key():
    # Missing API key
    with pytest.raises(ValueError) as exc:
        validate_env("", "url", "model")
    assert "API_KEY" in str(exc.value)


@pytest.mark.unit
def test_validate_env_failure_missing_all():
    # Missing all inputs
    with pytest.raises(ValueError) as exc:
        validate_env("", "", "")
    error_msg = str(exc.value)
    assert "API_KEY" in error_msg or "BASE_URL" in error_msg or "MODEL" in error_msg


# -------------------------------
# build_messages tests
# -------------------------------
@pytest.mark.unit
def test_build_messages_success():
    msg = build_messages("Hello")
    assert isinstance(msg, list)
    assert len(msg) > 0
    assert msg[0]["content"] == "Hello"


@pytest.mark.unit
def test_build_messages_empty_prompt():
    # Should still return a message structure even if prompt is empty
    msg = build_messages("")
    assert isinstance(msg, list)
    assert msg[0]["content"] == ""


@pytest.mark.unit
def test_build_messages_none_prompt():
    # Passing None should raise TypeError
    with pytest.raises(TypeError):
        build_messages(None)





# -------------------------------
# OpenAI response success
# -------------------------------

@pytest.mark.unit
def test_gemini_model_missing_env_unit(disable_rate_limit,monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','')
    monkeypatch.setenv('GEMINI_BASE_URL','')
    monkeypatch.setenv('GEMINI_MODEL_NAME','')

    with pytest.raises(ValueError) as exc:
        call_openai("Hello")
    assert "NOT FOUND" in str(exc.value)


# -------------------------------
# OpenAI API down (OpenAIError)
# -------------------------------
@pytest.mark.unit
@patch("app.main.OpenAI")
def test_gemini_model_openai_error_unit(mock_openai,disable_rate_limit,monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','test')
    monkeypatch.setenv('GEMINI_BASE_URL','test')
    monkeypatch.setenv('GEMINI_MODEL_NAME','test')

    mock_client = mock_openai.return_value
    mock_client.chat.completions.create.side_effect = OpenAIError("API down")

    with pytest.raises(OpenAIError) as exc:
        call_openai("Hello")
    assert "API down" in str(exc.value)


# -------------------------------
# Generic exception
# -------------------------------
@pytest.mark.unit
@patch("app.main.OpenAI")
def test_gemini_model_generic_error_unit(mock_openai,disable_rate_limit,monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','test')
    monkeypatch.setenv('GEMINI_BASE_URL','test')
    monkeypatch.setenv('GEMINI_MODEL_NAME','test')

    mock_client = mock_openai.return_value
    mock_client.chat.completions.create.side_effect = Exception("Something broke")

    with pytest.raises(Exception) as exc:
        call_openai("Hello")
    assert "Something broke" in str(exc.value)


# -------------------------------
# HTTPX connection error
# -------------------------------
@pytest.mark.unit
@patch("app.main.OpenAI")
def test_httpx_connection_error_unit(mock_openai,disable_rate_limit,monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','test')
    monkeypatch.setenv('GEMINI_BASE_URL','test')
    monkeypatch.setenv('GEMINI_MODEL_NAME','test')

    mock_client = mock_openai.return_value
    mock_client.chat.completions.create.side_effect = httpx.ConnectError("Network down")

    with pytest.raises(httpx.ConnectError) as exc:
        call_openai("Hi")
    assert "Network down" in str(exc.value)




# -------------------------------
# ✅ Helper: Fake streaming chunk
# -------------------------------
class FakeChunk:
    def __init__(self, content):
        self.choices = [
            MagicMock(delta=MagicMock(content=content))
        ]


# -------------------------------
# ✅ Test: Successful Streaming
# -------------------------------
@patch("app.main.OpenAI")
@patch("app.main.os.getenv")
def test_stream_success(mock_getenv, mock_openai):
    # Mock environment variables
    mock_getenv.side_effect = lambda key: {
        "GEMINI_API_KEY": "test_key",
        "GEMINI_BASE_URL": "test_url",
        "GEMINI_MODEL_NAME": "test_model"
    }.get(key)

    # Mock streaming response
    fake_stream = [
        FakeChunk("Hello"),
        FakeChunk(" "),
        FakeChunk("World")
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_stream
    mock_openai.return_value = mock_client

    # Call generator
    result = list(stream_response_func("Test prompt"))

    # Assertions
    assert result == [
        "data: Hello\n\n",
        "data:  \n\n",
        "data: World\n\n",
        "\n\n"
    ]


# -------------------------------
# ✅ Test: Missing ENV variables
# -------------------------------
@patch("app.main.os.getenv")
def test_stream_missing_env(mock_getenv):
    # Simulate missing API key
    mock_getenv.return_value = None

    result = list(stream_response_func("Test"))

    assert result == [
        "data: [ERROR: VENDOR API_KEY NOT FOUND..]\n\n"
    ]


# -------------------------------
# ✅ Test: OpenAI Exception
# -------------------------------
@patch("app.main.OpenAI")
@patch("app.main.os.getenv")
def test_stream_openai_exception(mock_getenv, mock_openai):
    # Mock valid env
    mock_getenv.side_effect = lambda key: {
        "GEMINI_API_KEY": "test_key",
        "GEMINI_BASE_URL": "test_url",
        "GEMINI_MODEL_NAME": "test_model"
    }.get(key)

    # Mock exception from API
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API failure")
    mock_openai.return_value = mock_client

    result = list(stream_response_func("Test"))

    assert result == [
        "data: [ERROR: API failure]\n\n"
    ]


# -------------------------------
# ✅ Test: Empty chunks ignored
# -------------------------------
@patch("app.main.OpenAI")
@patch("app.main.os.getenv")
def test_stream_empty_chunks(mock_getenv, mock_openai):
    mock_getenv.side_effect = lambda key: {
        "GEMINI_API_KEY": "test_key",
        "GEMINI_BASE_URL": "test_url",
        "GEMINI_MODEL_NAME": "test_model"
    }.get(key)

    fake_stream = [
        FakeChunk(None),
        FakeChunk("Hi"),
        FakeChunk("")
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_stream
    mock_openai.return_value = mock_client

    result = list(stream_response_func("Test"))

    assert result == [
        "data: Hi\n\n",
        "\n\n"
    ]
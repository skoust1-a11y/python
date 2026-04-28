import pytest
from unittest.mock import MagicMock, patch
from app.llm_app_service import LLMAppService
from openai import APIError

@pytest.fixture
def mock_cloud_client():
    mock_client = MagicMock()
    return mock_client

@pytest.fixture
def llm_service(mock_cloud_client):
    return LLMAppService(mock_cloud_client, "test-model")

def test_get_explanation_success(llm_service, mock_cloud_client):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Test explanation"))]
    mock_cloud_client.chat.completions.create.return_value = mock_response
    with patch("app.llm_app_service.insert_query_record") as mock_insert:
        result = llm_service.get_explanation("test concept")
        assert result == "Test explanation"
        mock_insert.assert_called_once()

def test_get_explanation_db_error(llm_service, mock_cloud_client):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Test explanation"))]
    mock_cloud_client.chat.completions.create.return_value = mock_response
    with patch("app.llm_app_service.insert_query_record", side_effect=Exception("DB error")):
        result = llm_service.get_explanation("test concept")
        assert result == "Test explanation"

def test_get_explanation_api_error(llm_service, mock_cloud_client):
    mock_cloud_client.chat.completions.create.side_effect = APIError("API error")
    with pytest.raises(APIError):
        llm_service.get_explanation("test concept")

def test_get_explanation_stream_success(llm_service, mock_cloud_client):
    mock_stream = [MagicMock(choices=[MagicMock(delta=MagicMock(content="chunk1"))]), MagicMock(choices=[MagicMock(delta=MagicMock(content="chunk2"))])]
    mock_cloud_client.chat.completions.create.return_value = mock_stream
    result = llm_service.get_explanation_stream("test concept")
    assert list(result) == mock_stream

def test_get_explanation_stream_error(llm_service, mock_cloud_client):
    mock_cloud_client.chat.completions.create.side_effect = Exception("stream error")
    with pytest.raises(Exception):
        list(llm_service.get_explanation_stream("test concept"))

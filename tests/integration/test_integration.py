import pytest
import time
from unittest.mock import patch,MagicMock
import httpx
from openai import OpenAIError
@pytest.mark.integration
@patch('app.main.OpenAI')
def test_explain_real_api(mock_openai, api_client, disable_rate_limit, monkeypatch):

    # Set env variables so validation doesn't fail
    monkeypatch.setenv('GEMINI_API_KEY', 'test')
    monkeypatch.setenv('GEMINI_BASE_URL', 'test')
    monkeypatch.setenv('GEMINI_MODEL_NAME', 'test-model')

    # Mock response structure
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="AI is the simulation of human intelligence."))
    ]

    # Mock OpenAI client
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client

    # Call API
    response = api_client.post('/explain', json={
        "prompt": "Explain what is AI in one sentence"
    })

    # Assertions
    assert response.status_code == 200

    data = response.json()

    assert "response" in data
    assert isinstance(data["response"], str)
    assert len(data["response"]) > 0

@pytest.mark.integration
@patch('app.main.OpenAI')
def test_personalize_real_api(mock_openai, api_client, disable_rate_limit, monkeypatch):

    # Set env variables
    monkeypatch.setenv('API_KEY_FOR_LOCAL','test')
    monkeypatch.setenv('BASE_URL_LOCAL','test')
    monkeypatch.setenv('LOCAL_MODEL','test-model')

    # Mock response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Cricket is a popular sport played worldwide."))
    ]

    # Mock OpenAI client
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client

    # Call API
    response = api_client.post('/personalize', json={
        "prompt": "Tell me about cricket"
    })

    # Assertions
    assert response.status_code == 200

    data = response.json()

    assert "response" in data
    assert isinstance(data["response"], str)
    assert len(data["response"]) > 0

    # Optional stronger assertions (recommended)
    assert data["response"] == "Cricket is a popular sport played worldwide."
    assert data["status"] == 200
    assert data["message"] == "Success"

    
@pytest.mark.integration
def test_streaming_endpoint_format(api_client):
    """Test that streaming endpoint follows SSE format"""
    time.sleep(65)  # Avoid rate limit
    
    request_data = {"prompt": "Say hello"}
    
    with api_client.stream("POST", "/explain/stream", json=request_data) as response:
        # Verify response started successfully
        assert response.status_code == 200
        assert response.headers.get("content-type") == "text/event-stream; charset=utf-8"
        
        # Collect and verify SSE format
        lines = []
        for line in response.iter_lines():
            if line:  # Skip empty lines
                lines.append(line)
                # Assert each data line starts with "data: "
                if line.strip():  # Non-empty lines
                    assert line.startswith('data: '), \
                        f"Line should start with 'data: ' but got: {line}"
        
        # Verify we received content
        assert len(lines) > 0, "Should receive at least one data line"
        
        # Verify content (extract data after "data: " prefix)
        full_content = ''.join([line.replace('data: ', '') for line in lines])
        assert len(full_content) > 0, "Should have actual content after 'data: ' prefix"


@pytest.mark.integration
def test_explain_validation_error(api_client):

    response = api_client.post('/explain', json={})

    assert response.status_code == 422

@pytest.mark.integration
def test_personalize_validation_error(api_client):

    response = api_client.post('/personalize', json={})

    assert response.status_code == 422

@pytest.mark.integration
def test_explain_missing_env(api_client,monkeypatch):
    import os

    monkeypatch.setenv('GEMINI_API_KEY','')
    monkeypatch.setenv('GEMINI_BASE_URL','')
    monkeypatch.setenv('GEMINI_MODEL_NAME','')

    response = api_client.post('/explain', json={
        "prompt": "Hello"
    })

    assert response.status_code == 400

@pytest.mark.integration
def test_explain_rate_limit(api_client):
    import time

    # Reset window
    time.sleep(65)

    for _ in range(3):
        api_client.post('/explain', json={"prompt": "Hi"})

    response = api_client.post('/explain', json={"prompt": "Hi"})

    assert response.status_code == 429


@pytest.mark.integration
def test_personalize_missing_env(api_client,monkeypatch):
    import os


    monkeypatch.setenv('API_KEY_FOR_LOCAL','')
    monkeypatch.setenv('BASE_URL_LOCAL','')
    monkeypatch.setenv('LOCAL_MODEL','')

    response = api_client.post('/personalize', json={
        "prompt": "Hello"
    })

    assert response.status_code == 400

@pytest.mark.integration
def test_stream_validation_error(api_client):

    response = api_client.post('/explain/stream', json={})

    content = response.text

    # Streaming returns error inside data, not status code
    assert "ERROR" in content

@pytest.mark.integration
def test_stream_missing_env(api_client,monkeypatch):
    import os
    import time

    time.sleep(65)  # avoid rate limit

    monkeypatch.setenv('GEMINI_API_KEY','')
    monkeypatch.setenv('GEMINI_BASE_URL','')
    monkeypatch.setenv('GEMINI_MODEL_NAME','')

    response = api_client.post('/explain/stream', json={
        "prompt": "Hello"
    })

    content = response.text

    # Streaming returns error inside data, not status code
    assert "ERROR" in content


@pytest.mark.integration
def test_explain_env_validation_400(api_client,monkeypatch):
    import os

    monkeypatch.setenv('GEMINI_API_KEY','')
    monkeypatch.setenv('GEMINI_BASE_URL','')
    monkeypatch.setenv('GEMINI_MODEL_NAME','')

    response = api_client.post('/explain', json={
        "prompt": "Hello"
    })

    assert response.status_code == 400
    assert "NOT FOUND" in response.json()["detail"]

@pytest.mark.integration
def test_personalize_env_validation_400(api_client,monkeypatch):
    import os

    monkeypatch.setenv('API_KEY_FOR_LOCAL','')
    monkeypatch.setenv('BASE_URL_LOCAL','')
    monkeypatch.setenv('LOCAL_MODEL','')

    response = api_client.post('/personalize', json={
        "prompt": "Hello"
    })

    assert response.status_code == 400

@pytest.mark.integration
def test_stream_env_error(api_client,monkeypatch):
    import os

    monkeypatch.setenv('GEMINI_API_KEY','')
    
    response = api_client.post('/explain/stream', json={
        "prompt": "Hello"
    })

    assert "ERROR" in response.text


@pytest.mark.integration
@patch('app.main.OpenAI')
def test_gemini_response_model(mock_openai, api_client,disable_rate_limit,monkeypatch):

    """
    #Set env variables so validation doesn't fail
    # Mock response structure
    # Mock OpenAI instance
    #Call API
    #Assertions"""
    import os
    monkeypatch.setenv('GEMINI_API_KEY','test')
    monkeypatch.setenv('GEMINI_BASE_URL','test')
    monkeypatch.setenv('GEMINI_MODEL_NAME','test-model')


    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="FAKE AI RESPONSE"))
    ]

   
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    mock_openai.return_value = mock_client

  
    response = api_client.post('/explain', json={
        "prompt": "Hello World"
    })

   
    assert response.status_code == 200

    data = response.json()

    assert data["response"] == "FAKE AI RESPONSE"
    assert data["status"] == 200
    assert data["message"] == "Success"

@pytest.mark.integration
@patch('app.main.load_dotenv')
def test_gemini_model_missing_env(mock_dotenv, api_client,disable_rate_limit,monkeypatch):
    import os

    monkeypatch.setenv('GEMINI_API_KEY','')
    monkeypatch.setenv('GEMINI_BASE_URL','')
    monkeypatch.setenv('GEMINI_MODEL_NAME','')

    response = api_client.post('/explain', json={
        "prompt": "Hello"
    })

    assert response.status_code == 400
    assert "NOT FOUND" in response.json()["detail"]



@pytest.mark.integration
@patch('app.main.OpenAI')
def test_gemini_model_openai_error(mock_openai, api_client,disable_rate_limit,monkeypatch):
    import os

    monkeypatch.setenv('GEMINI_API_KEY','')
    monkeypatch.setenv('GEMINI_BASE_URL','')
    monkeypatch.setenv('GEMINI_MODEL_NAME','')

    mock_client = mock_openai.return_value
    mock_client.chat.completions.create.side_effect = OpenAIError("API down")

    response = api_client.post('/explain', json={
        "prompt": "Hello"
    })

    assert response.status_code == 502
    assert "not working" in response.json()["detail"]

@pytest.mark.integration
@patch('app.main.OpenAI')
def test_gemini_model_generic_error(mock_openai, api_client,disable_rate_limit,monkeypatch):
    import os

    monkeypatch.setenv('GEMINI_API_KEY','test')
    monkeypatch.setenv('GEMINI_BASE_URL','test')
    monkeypatch.setenv('GEMINI_MODEL_NAME','test')

    mock_client = mock_openai.return_value
    mock_client.chat.completions.create.side_effect = Exception("Something broke")

    response = api_client.post('/explain', json={
        "prompt": "Hello"
    })

    assert response.status_code == 500

@pytest.mark.integration
@patch("app.main.OpenAI")
def test_httpx_connection_error(mock_openai, api_client,disable_rate_limit,monkeypatch):
    import os

    monkeypatch.setenv('GEMINI_API_KEY','test')
    monkeypatch.setenv('GEMINI_BASE_URL','test')
    monkeypatch.setenv('GEMINI_MODEL_NAME','test')

    mock_client = mock_openai.return_value
    mock_client.chat.completions.create.side_effect = httpx.ConnectError("Network down")

    response = api_client.post('/explain', json={"prompt": "Hi"})

    assert response.status_code == 502
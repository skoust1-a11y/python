import logging

from ..config.settings import settings
from openai import OpenAI, OpenAIError
from httpx import ConnectError
from typing import Iterator

# from ..exceptions.Custom_Exceptions import MissingEnvVarError

logger = logging.getLogger(__name__)


def prompt_generate(prompt: str):
    logger.debug(f"Generating prompt messages for input: '{prompt[:80]}...'")
    messages = [
        {
            'role': 'user',
            'content': prompt
        }
    ]
    logger.debug(f"Prompt messages generated: {len(messages)} message(s)")
    return messages


def require_env(var_name, value):
    if not value:
        raise RuntimeError(f"Required environment variable '{var_name}' is missing or empty.")
    return value


# Maintain all base url, model type, api key in .env and access them here using settings.get_env() method.
# This way we can easily switch between different LLMs by just changing the .env file without modifying the codebase.
def call_gemini_llm(prompt: str):
    logger.info("Calling Gemini LLM")
    logger.debug(f"Prompt (first 100 chars): '{prompt[:100]}...'")
    try:
        open_ai_key = require_env('OPENAI_API_KEY', settings.get_env("OPENAI_API_KEY"))
        gemini_url = require_env('OPENAI_BASE_URL', settings.get_env("OPENAI_BASE_URL"))
        gemini_model = require_env('OPENAI_MODEL', settings.get_env("OPENAI_MODEL"))

        logger.debug(f"Using Gemini model: {gemini_model}, base URL: {gemini_url}")
        client = OpenAI(api_key=open_ai_key, base_url=gemini_url)
        response = client.chat.completions.create(
            model=gemini_model,
            messages=prompt_generate(prompt=prompt)
        )
        content = response.choices[0].message.content
    except RuntimeError as e:
        raise RuntimeError(f'Env config missing error : {str(e)}')
    except ConnectError as e:
        logger.error(f"Connection failed to Gemini endpoint: {e}")
        raise ConnectError(f'Connection Failed : {str(e)}')
    except OpenAIError as e:
        logger.error(f"OpenAI SDK error during Gemini call: {e}")
        raise OpenAIError(f'OPENAI SDK ERROR : {str(e)}')
    except Exception as e:
        logger.exception(f"Unexpected error during Gemini LLM call: {e}")
        raise Exception(f'ERROR :{str(e)}')

    return content


def call_gemma_llm(prompt: str):
    logger.info("Calling Gemma LLM via Ollama")
    logger.debug(f"Prompt (first 100 chars): '{prompt[:100]}...'")
    try:
        ollama_api_key = require_env('OLLAMA_API_KEY', settings.get_env("OLLAMA_API_KEY"))
        ollama_model = require_env('OLLAMA_MODEL', settings.get_env("OLLAMA_MODEL"))
        ollama_base_url = require_env('OLLAMA_BASE_URL', settings.get_env("OLLAMA_BASE_URL"))

        logger.debug(f"Using Ollama model: {ollama_model}, base URL: {ollama_base_url}")
        client = OpenAI(api_key=ollama_api_key, base_url=ollama_base_url)
        response = client.chat.completions.create(
            model=ollama_model,
            messages=prompt_generate(prompt=prompt)
        )
    except RuntimeError as e:
        raise RuntimeError(f'Env config missing error : {str(e)}')
    except ConnectError as e:
        logger.error(f"Connection failed to Ollama endpoint: {e}")
        raise ConnectError(f'Connection Failed : {str(e)}')
    except OpenAIError as e:
        logger.error(f"OpenAI SDK error during Gemma call: {e}")
        raise OpenAIError(f'OPENAI SDK ERROR : {str(e)}')
    except Exception as e:
        logger.exception(f"Unexpected error during Gemma LLM call: {e}")
        raise Exception(f'ERROR :{str(e)}')
        
    return response.choices[0].message.content


def call_llm_gemini_stream(prompt: str) -> Iterator[str]:
    try:
        open_ai_key = require_env('OPENAI_API_KEY', settings.get_env("OPENAI_API_KEY"))
        gemini_url = require_env('OPENAI_BASE_URL', settings.get_env("OPENAI_BASE_URL"))
        gemini_model = require_env('OPENAI_MODEL', settings.get_env("OPENAI_MODEL"))

        client = OpenAI(api_key=open_ai_key, base_url=gemini_url)
        stream = client.chat.completions.create(
            model=gemini_model,
            messages=prompt_generate(prompt=prompt),
            stream=True,
        )
    except RuntimeError as e:
        raise RuntimeError(f'Env config missing error : {str(e)}')
    except ConnectError as e:
        raise ConnectError(f'Connection Failed : {str(e)}')
    except OpenAIError as e:
        raise OpenAIError(f'OPENAI SDK ERROR : {str(e)}')
    except Exception as e:
        raise Exception(f'ERROR :{str(e)}')

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if not delta:
            continue
        content = delta.content
        if content:
            yield content


def call_llm_gemma_stream(prompt: str) -> Iterator[str]:
    try:
        ollama_api_key = require_env('OLLAMA_API_KEY', settings.get_env("OLLAMA_API_KEY"))
        ollama_model = require_env('OLLAMA_MODEL', settings.get_env("OLLAMA_MODEL"))
        ollama_base_url = require_env('OLLAMA_BASE_URL', settings.get_env("OLLAMA_BASE_URL"))

        client = OpenAI(api_key=ollama_api_key, base_url=ollama_base_url)
        stream = client.chat.completions.create(
            model=ollama_model,
            messages=prompt_generate(prompt=prompt),
            stream=True,
        )
    except RuntimeError as e:
        raise RuntimeError(f'Env config missing error : {str(e)}')
    except ConnectError as e:
        raise ConnectError(f'Connection Failed : {str(e)}')
    except OpenAIError as e:
        raise OpenAIError(f'OPENAI SDK ERROR : {str(e)}')
    except Exception as e:
        raise Exception(f'ERROR :{str(e)}')

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if not delta:
            continue
        content = delta.content
        if content:
            yield content

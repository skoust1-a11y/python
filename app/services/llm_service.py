from ..config import settings
from openai import OpenAI,OpenAIError
from httpx import ConnectError
from exceptions.Custom_Exceptions import MissingEnvVarError

def prompt_generate(prompt : str):
    messages = [
        {
            'role':'user',
            'content':prompt
        }
    ]
    return messages

def require_env(var_name, value):
    if not value:
        raise MissingEnvVarError(f"Required environment variable '{var_name}' is missing or empty.")
    return value


#Maintain all base url , model type , api key in .env and access them here using settings.get_env() method. This way we can easily switch between different LLMs by just changing the .env file without modifying the codebase.
def call_gemini_llm(prompt: str):
    # Placeholder for LLM interaction
    try:
        open_ai_key = require_env('OPENAI_API_KEY',settings.get_env("OPENAI_API_KEY"))
        gemini_url = require_env('OPENAI_BASE_URL',settings.get_env("OPENAI_BASE_URL"))
        gemini_model = require_env('OPENAI_MODEL',settings.get_env("OPENAI_MODEL"))

        client = OpenAI(api_key=open_ai_key,base_url=gemini_url)
        response = client.chat.completions.create(
            model=gemini_model,
            messages=prompt_generate(prompt=prompt)
        )
    except MissingEnvVarError as e:
        raise RuntimeError(f'Env config missing error : {str(e)}')
    except ConnectError as e:
        raise ConnectError(f'Connection Failed : {str(e)}')
    except OpenAIError as e:
        raise OpenAIError(f'OPENAI SDK ERROR : {str(e)}')
    except Exception as e:
        raise Exception(f'ERROR :{str(e)}')
        
    return response.choices[0].message.content


def call_gemma_llm(prompt: str):
    # Placeholder for LLM interaction
    try:
        ollama_api_key = require_env('OLLAMA_API_KEY',settings.get_env("OLLAMA_API_KEY"))
        ollama_model = require_env('OLLAMA_MODEL',settings.get_env("OLLAMA_MODEL"))
        ollama_base_url = require_env('OLLAMA_BASE_URL',settings.get_env("OLLAMA_BASE_URL"))

        client = OpenAI(api_key=ollama_api_key,base_url=ollama_base_url)
        response = client.chat.completions.create(
            model=ollama_model,
            messages=prompt_generate(prompt=prompt)
        )
    except MissingEnvVarError as e:
        raise RuntimeError(f'Env config missing error : {str(e)}')
    except ConnectError as e:
        raise ConnectError(f'Connection Failed : {str(e)}')
    except OpenAIError as e:
        raise OpenAIError(f'OPENAI SDK ERROR : {str(e)}')
    except Exception as e:
        raise Exception(f'ERROR :{str(e)}')
        
    return response.choices[0].message.content
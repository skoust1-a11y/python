from fastapi import FastAPI, HTTPException, Request, Body
from openai import OpenAI, OpenAIError
from app.schemas import PromptModel, AnswerModel
import os
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi.responses import StreamingResponse
import httpx

app = FastAPI(
    title='Agentic AI LLM Service',
    description="An API for interacting with a Gemini-powered LLM."
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ✅ ---------------- HELPERS ----------------

def validate_env(api_key, base_url, ai_model):
    if not api_key:
        raise ValueError('VENDOR API_KEY NOT FOUND..')
    if not base_url:
        raise ValueError('VENDOR BASE_URL NOT FOUND')
    if not ai_model:
        raise ValueError('AI_MODEL NOT AVAILABLE')


def build_messages(prompt: str):
    return [
        {
            'role': 'user',
            'content': prompt
        }
    ]


# ✅ ---------------- STREAM ----------------

def stream_response_func(prompt: str):
    load_dotenv()

    api_key = os.getenv('GEMINI_API_KEY')
    base_url = os.getenv('GEMINI_BASE_URL')
    ai_model = os.getenv('GEMINI_MODEL_NAME')

    try:
        validate_env(api_key, base_url, ai_model)
    except ValueError as e:
        yield f"data: [ERROR: {str(e)}]\n\n"
        return

    messages = build_messages(prompt)

    try:
        client = OpenAI(base_url=base_url, api_key=api_key)

        response = client.chat.completions.create(
            model=ai_model,
            messages=messages,
            stream=True,
            temperature=0.2
        )

        for chunk in response:
            content = chunk.choices[0].delta.content or ""
            if content:
                yield f'data: {content}\n\n'

        yield '\n\n'

    except Exception as e:
        yield f"data: [ERROR: {str(e)}]\n\n"


@app.post('/explain/stream')
@limiter.limit('3/minute')
def stream_response_by_llm(request: Request, prompt: PromptModel):
    return StreamingResponse(
        content=stream_response_func(prompt=prompt.prompt),
        media_type='text/event-stream'
    )


# ✅ ---------------- EXPLAIN ----------------

@app.post('/explain', response_model=AnswerModel)
@limiter.limit('3/minute')
def gemini_response_model(request: Request, prompt: PromptModel):
    try:
        payload = call_openai(prompt.prompt)

        return AnswerModel(
                status=200,
                message='Success',
                response=payload
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except (OpenAIError ,httpx.HTTPError) as e:
        raise HTTPException(
            status_code=502,
            detail=f'The AI Model LLM not working and the error is {str(e)}'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ ---------------- PERSONALIZE ----------------

@app.post('/personalize', response_model=AnswerModel)
@limiter.limit('3/minute')
def local_model(request: Request, prompt: PromptModel = Body(...)):
    load_dotenv()

    api_key = os.getenv('API_KEY_FOR_LOCAL')
    base_url = os.getenv('BASE_URL_LOCAL')
    ai_model = os.getenv('LOCAL_MODEL')

    try:
        validate_env(api_key, base_url, ai_model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    messages = build_messages(
        f'Give me a personalized summary on this for 200 words\n{prompt.prompt}'
    )

    try:
        client = OpenAI(base_url=base_url, api_key=api_key)

        response = client.chat.completions.create(
            model=ai_model,
            messages=messages
        )

        payload = response.choices[0].message.content

        return AnswerModel(
            status=200,
            message='Success',
            response=payload
        )

    except OpenAIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
def call_openai(prompt: str):
    load_dotenv()

    api_key = os.getenv('GEMINI_API_KEY')
    base_url = os.getenv('GEMINI_BASE_URL')
    ai_model = os.getenv('GEMINI_MODEL_NAME')

    # ✅ validate env (unit test expects ValueError)
    validate_env(api_key, base_url, ai_model)

    messages = build_messages(prompt)

    try:
        client = OpenAI(base_url=base_url, api_key=api_key)

        response = client.chat.completions.create(
            model=ai_model,
            messages=messages,
            temperature=0.1
        )

        return response.choices[0].message.content

    # ✅ let these propagate (unit tests expect them)
    except OpenAIError:
        raise
    except httpx.HTTPError:
        raise
    except Exception:
        raise
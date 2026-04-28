from fastapi import FastAPI,HTTPException,Request
from openai import OpenAI,OpenAIError
from schemas import PromptModel,AnswerModel
import os
from dotenv import load_dotenv
from slowapi import Limiter,_rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi.responses import StreamingResponse
"""
Sprint-7: FAST-API,SLOW-API

This example demonstrates how to add rate limiting to protect your API
from abuse and control costs by limiting requests per IP address.
"""

app =FastAPI(
    title='Agentic AI LLM Service',
    description= "An API for interacting with a Gemini-powered LLM. "
        "It provides both streaming and non-streaming responses, "
        "ideal for chatbots and intelligent assistants."
)

limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded,_rate_limit_exceeded_handler)


def stream_response_func(prompt : str):
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    base_url = os.getenv('GEMINI_BASE_URL')
    ai_model = os.getenv('GEMINI_MODEL_NAME')

    if not api_key:
        raise ValueError('ENDOR API_KEY NOT FOUND..')
    if not base_url:
        raise ValueError('VENDOR BASE_URL NOT FOUND')
    if not ai_model:
        raise ValueError('AI_MODEL NOT AVAILABLE')
    
    messages = [
        {
            'role':'user',
            'content':prompt
        }
    ]
    try:
        client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
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
    except RateLimitExceeded as e:
        yield f"data: [ERROR: {str(e)}]\n\n"
    except ValueError as e:
        yield f"data: [ERROR: {str(e)}]\n\n"
    except OpenAIError as e :
        yield f"data: [ERROR: {str(e)}]\n\n"
    except Exception as e:
        yield f"data: [ERROR: {str(e)}]\n\n"

@app.post('/explain/stream',summary='Streaming Response By LLM')
@limiter.limit('3/minute')
def stream_response_by_llm(request : Request , prompt : PromptModel):
    """
    ### 🔹 Description
    Streams AI-generated response in real-time instead of returning a full JSON.

    ### 🔹 Response
    - **200**: Streamed text chunks (plain text/event-stream)

    ### 🔹 Notes
    - Useful for chat/AI responses
    - Data is sent incrementally as it is generated
    """
    return StreamingResponse(
        content=stream_response_func(prompt=prompt.prompt),
        media_type='text/event-stream'
    )

@app.post('/explain',response_model=AnswerModel,summary='FACTUAL ANSWERS FOR VENDOR SIDE')
@limiter.limit('3/minute')
def gemini_response_model(request : Request,prompt : PromptModel):
    """ ### 🔹 Description
    This endpoint generates a FACTUAL DATA  using a GEMINI AI model.

    ### 🔹 Request Body
    - **prompt**: Input text for which summary needs to be generated.

    ### 🔹 Responses
    - **200**: Successful response with generated summary
    - **401**: AI model error / authentication issue
    - **500**: Missing environment variables or server issue
    - **429**: Rate limit exceeded

    ### 🔹 Notes
    - Rate limited to **3 requests per minute**
    - Requires environment variables:
        - API_KEY_FOR_LOCAL
        - BASE_URL_LOCAL
        - LOCAL_MODEL
    """
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    base_url = os.getenv('GEMINI_BASE_URL')
    ai_model = os.getenv('GEMINI_MODEL_NAME')

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail='VENDOR API_KEY NOT FOUND..'
        )
    if not base_url:
        raise HTTPException(
            status_code=400,
            detail='VENDOR BASE_URL NOT FOUND'
        )
    if not ai_model:
        raise HTTPException(
            status_code=400,
            detail='AI_MODEL NOT AVAILABLE'
        )
    
    messages = [
        {
            'role':'user',
            'content':prompt.prompt
        }
    ]
    
    try:
        client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        response = client.chat.completions.create(
            model=ai_model,
            messages=messages,
            temperature=0.1
        )

        payload = response.choices[0].message.content

        return AnswerModel(
            status=200,
            message='Success',
            response=payload
        )
    except OpenAIError as e :
        raise HTTPException(
            status_code=502,
            detail=f'The AI Model LLM not working and the error is {str(e)}'
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail = str(e)
        )

@app.post('/personalize',response_model=AnswerModel,summary='LOCAL MODEL FOR STORY KIND OF TELLLING')
@limiter.limit('3/minute')
def local_model(request : Request,prompt : PromptModel):
    """  ### 🔹 Description
    This endpoint generates a personalized 200-word summary using a local AI model.

    ### 🔹 Request Body
    - **prompt**: Input text for which summary needs to be generated.

    ### 🔹 Responses
    - **200**: Successful response with generated summary
    - **401**: AI model error / authentication issue
    - **500**: Missing environment variables or server issue
    - **429**: Rate limit exceeded

    ### 🔹 Notes
    - Rate limited to **3 requests per minute**
    - Requires environment variables:
        - API_KEY_FOR_LOCAL
        - BASE_URL_LOCAL
        - LOCAL_MODEL
    """
    load_dotenv()
    api_key = os.getenv('API_KEY_FOR_LOCAL')
    base_url = os.getenv('BASE_URL_LOCAL')
    ai_model = os.getenv('LOCAL_MODEL')

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail='VENDOR API_KEY NOT FOUND..'
        )
    if not base_url:
        raise HTTPException(
            status_code=400,
            detail='VENDOR BASE_URL NOT FOUND'
        )
    if not ai_model:
        raise HTTPException(
            status_code=400,
            detail='AI_MODEL NOT AVAILABLE'
        )
    
    messages = [
        {
            'role':'user',
            'content':f'Give me a personalized summary on this for 200 words for this question\n{prompt.prompt}'
        }
    ]
    
    try:
        client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
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
    except OpenAIError as e :
        raise HTTPException(
            status_code=502,
            detail=f'The AI Model LLM not working and the error is {str(e)}'
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail = str(e)
        )



def main():
    print("Hello from p1-ai-tutor-with-rest-api!")


if __name__ == "__main__":
    main()

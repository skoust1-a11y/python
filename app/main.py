


from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI, APIError
import os
import logging
import json
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .schemas import ConceptRequest, ExplanationResponse


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
base_url = os.getenv("GEMINI_BASE_URL")
model = os.getenv("GEMINI_MODEL")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file!")


CLOUD_CLIENT = OpenAI(api_key=api_key, base_url=base_url)
CLOUD_MODEL = model


limiter = Limiter(key_func=get_remote_address)


app = FastAPI(
    title="AI Tutor API",
    description="AI Tutor with Cloud Models",
    version="2.0.0"
)


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.post(
    "/explain",
    response_model=ExplanationResponse,
    tags=["Explanations"],
    summary="Get Factual Explanation",
    responses={
        200: {"description": "Successful explanation"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"}
    }
)
@limiter.limit("2/minute")  # 2 requests per minute per IP address
def get_explanation(request: Request, concept_request: ConceptRequest):
   
    try:
        logger.info(f"Processing explanation request for concept: {concept_request.concept}")
        # Call AI model
        messages = [{
            "role": "user",
            "content": f"Explain {concept_request.concept} in Agentic AI clearly and concisely for a beginner."
        }]
        
        response = CLOUD_CLIENT.chat.completions.create(model=CLOUD_MODEL, messages=messages)
        explanation = response.choices[0].message.content
        logger.info(f"Successfully generated explanation for concept: {concept_request.concept}")
        
        return ExplanationResponse(
            concept=concept_request.concept,
            explanation=explanation,
            model=CLOUD_MODEL
        )
    except APIError as e:
        logger.error(f"API Error while processing explanation request: {e}")
        raise HTTPException(status_code=500, detail={"error": "API Error", "message": str(e)})
    except Exception as e:
        logger.error(f"Internal Error while processing explanation request: {e}")
        raise HTTPException(status_code=500, detail={"error": "Internal Error", "message": str(e)})

@app.post(
    "/explain/stream",
    tags=["Explanations"],
    summary="Get Streaming Explanation",
    responses={
        200: {"description": "Streaming explanation"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"}
    }
)
@limiter.limit("2/minute")  # 2 requests per minute per IP address
def get_explanation_stream(request: Request, concept_request: ConceptRequest):
   
    def format_sse(data: dict) -> str:
       
        return f"data: {json.dumps(data)}\n\n"
    
    async def generate_stream():
        try:
            logger.info(f"Streaming explanation for: {concept_request.concept}")
            
            # Get streaming response from AI model
            stream = CLOUD_CLIENT.chat.completions.create(
                model=CLOUD_MODEL,
                messages=[{
                    "role": "user",
                    "content": f"Explain {concept_request.concept} in Agentic AI clearly and concisely for a beginner."
                }],
                stream=True
            )
            
            # Send metadata
            yield format_sse({
                "type": "metadata",
                "concept": concept_request.concept,
                "model": CLOUD_MODEL
            })
            
            # Stream content chunks
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield format_sse({"type": "content", "content": content})
            
            # Send completion signal
            yield format_sse({"type": "done"})
            logger.info(f"Completed streaming for: {concept_request.concept}")
            
        except Exception as e:
            error_type = "API Error" if isinstance(e, APIError) else "Internal Error"
            logger.error(f"{error_type} in streaming: {e}")
            yield format_sse({
                "type": "error",
                "error": error_type,
                "message": str(e)
            })
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/", tags=["System"], summary="API Information")
def root():
   
    return {
        "name": "AI Tutor API",
        "version": "2.0.0",
        "description": "Personalized Learning with Cloud AI Models",
        "documentation": {
            "interactive": "/docs",
            "redoc": "/redoc"
        },
        "endpoints": {
            "explain": "/explain",
            "explain/stream": "/explain/stream"
        }
    }
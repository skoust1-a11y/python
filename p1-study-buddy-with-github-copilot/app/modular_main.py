"""Refactored FastAPI entrypoint using route handlers + service layer."""

import json
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import APIError, OpenAI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .db_operations import init_db, insert_query_record
from .llm_app_service import (
    build_explanation_prompt,
    generate_explanation,
    generate_explanation_stream,
)
from .schemas import ConceptRequest, ExplanationResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
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
    version="2.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """Ensure database tables exist before serving requests."""
    init_db()


@app.post(
    "/explain",
    response_model=ExplanationResponse,
    tags=["Explanations"],
    summary="Get Factual Explanation",
)
@limiter.limit("2/minute")
def get_explanation(request: Request, concept_request: ConceptRequest):
    """Route for generating and persisting one complete explanation."""
    try:
        explanation = generate_explanation(CLOUD_CLIENT, CLOUD_MODEL, concept_request.concept)
        insert_query_record(
            concept=concept_request.concept,
            query_text=build_explanation_prompt(concept_request.concept),
            explanation=explanation,
            model=CLOUD_MODEL,
        )
        return ExplanationResponse(
            concept=concept_request.concept,
            explanation=explanation,
            model=CLOUD_MODEL,
        )
    except APIError as exc:
        logger.error("API Error while processing explanation request: %s", exc)
        raise HTTPException(status_code=500, detail={"error": "API Error", "message": str(exc)})
    except Exception as exc:
        logger.error("Internal Error while processing explanation request: %s", exc)
        raise HTTPException(status_code=500, detail={"error": "Internal Error", "message": str(exc)})


@app.post(
    "/explain/stream",
    tags=["Explanations"],
    summary="Get Streaming Explanation",
)
@limiter.limit("2/minute")
def get_explanation_stream(request: Request, concept_request: ConceptRequest):
    """Route for streaming explanation chunks and persisting combined content."""

    def format_sse(data: dict) -> str:
        return f"data: {json.dumps(data)}\\n\\n"

    async def generate_stream():
        parts: list[str] = []
        try:
            yield format_sse(
                {
                    "type": "metadata",
                    "concept": concept_request.concept,
                    "model": CLOUD_MODEL,
                }
            )
            for piece in generate_explanation_stream(CLOUD_CLIENT, CLOUD_MODEL, concept_request.concept):
                parts.append(piece)
                yield format_sse({"type": "content", "content": piece})

            insert_query_record(
                concept=concept_request.concept,
                query_text=build_explanation_prompt(concept_request.concept),
                explanation="".join(parts),
                model=CLOUD_MODEL,
            )
            yield format_sse({"type": "done"})
        except Exception as exc:
            error_type = "API Error" if isinstance(exc, APIError) else "Internal Error"
            logger.error("%s in streaming: %s", error_type, exc)
            yield format_sse({"type": "error", "error": error_type, "message": str(exc)})

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/", tags=["System"], summary="API Information")
def root():
    """Return API metadata and endpoint references."""
    return {
        "name": "AI Tutor API",
        "version": "2.0.0",
        "description": "Personalized Learning with Cloud AI Models",
        "documentation": {"interactive": "/docs", "redoc": "/redoc"},
        "endpoints": {"explain": "/explain", "explain/stream": "/explain/stream"},
    }

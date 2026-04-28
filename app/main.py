import os
import asyncio
from http import HTTPStatus
from datetime import datetime
from typing import AsyncGenerator, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import requests
from openai import AsyncOpenAI

from app.schemas import (
    ConceptRequest,
    ErrorResponse,
    ExplanationResponse,
    PersonalizedResponse,
    RateLimitError,
    StreamChunk,
)

# Load environment variables
load_dotenv()


# Initialize FastAPI app
app = FastAPI(
    title=os.getenv("API_TITLE", "Study Buddy AI Tutor API"),
    description="Personalized AI Tutor with REST API, streaming, and rate limiting",
    version=os.getenv("API_VERSION", "1.0.0"),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Add rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=RateLimitError(
            error="RateLimitExceeded",
            detail=str(exc.detail),
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            timestamp=datetime.now(),
            retry_after=60,
        ).model_dump(mode="json"),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Convert FastAPI validation errors to assignment-aligned 400 responses."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error="ValidationError",
            detail=str(exc.errors()),
            status_code=status.HTTP_400_BAD_REQUEST,
            timestamp=datetime.now(),
        ).model_dump(mode="json"),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Return consistent error payloads for handled HTTP exceptions."""
    try:
        error_name = HTTPStatus(exc.status_code).phrase
    except ValueError:
        error_name = "HTTPException"

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=error_name,
            detail=str(exc.detail),
            status_code=exc.status_code,
            timestamp=datetime.now(),
        ).model_dump(mode="json"),
    )


# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv(
    "OPENAI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
)
CLOUD_MODEL = os.getenv("CLOUD_MODEL", "gemini-2.0-flash")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
RATE_LIMIT = os.getenv("RATE_LIMIT_PER_MINUTE", "3")


class TutorAI:
    """AI Tutor service that handles cloud and local model interactions."""

    def __init__(self):
        """Initialize the AI Tutor with API configurations."""
        self.openai_api_key = OPENAI_API_KEY
        self.cloud_model = CLOUD_MODEL
        self.cloud_client = (
            AsyncOpenAI(
                api_key=self.openai_api_key,
                base_url=OPENAI_BASE_URL,
            )
            if self.openai_api_key
            else None
        )
        self.ollama_url = OLLAMA_BASE_URL
        self.ollama_model = OLLAMA_MODEL

    def _validate_cloud_client(self) -> bool:
        """Validate cloud client configuration for OpenAI-compatible Gemini access."""
        if not self.cloud_client:
            return False
        return True

    def _validate_ollama_connection(self) -> bool:
        """Validate connection to Ollama server."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    async def explain_with_cloud_model(
        self, concept: str, learning_level: str, context: Optional[str] = None
    ) -> str:
        """
        Generate explanation using cloud model (Gemini).

        Args:
            concept: The concept to explain
            learning_level: The target learning level
            context: Optional additional context

        Returns:
            Explanation string
        """
        if not self._validate_cloud_client():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cloud API key is not configured. Please set OPENAI_API_KEY in .env file.",
            )

        prompt = (
            f"Explain the concept '{concept}' at a {learning_level} level. "
            "Give a clear, accurate, and structured explanation. "
            "Include 2-3 practical examples."
        )
        if context:
            prompt += f" Learner context: {context}"

        try:
            completion = await self.cloud_client.chat.completions.create(
                model=self.cloud_model,
                temperature=0.3,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Study Buddy, a factual and concise AI tutor. "
                            "Tailor explanations to requested learning level."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            return (completion.choices[0].message.content or "").strip()

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error from cloud model: {str(e)}",
            )

    async def personalize_with_local_model(
        self, concept: str, context: Optional[str] = None
    ) -> str:
        """
        Generate personalized explanation using local model (Ollama).

        Args:
            concept: The concept to explain
            context: Optional additional context

        Returns:
            Personalized explanation string
        """
        if not self.ollama_url or not self.ollama_model:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OLLAMA_BASE_URL or OLLAMA_MODEL is not configured in .env.",
            )

        if not self._validate_ollama_connection():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Ollama service is not available at {self.ollama_url}. "
                "Please ensure Ollama is running: ollama serve",
            )

        prompt = f"""Create a creative, personalized explanation for the concept: '{concept}'
        {f'with context: {context}' if context else ''}
        
        Use analogies, storytelling, or relatable examples to make it fun and memorable.
        Keep it concise but engaging."""

        try:
            # Make request to Ollama
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=30,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Ollama error: {response.text}",
                )

            return response.json().get("response", "").strip()

        except requests.exceptions.Timeout:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Ollama request timed out. The model might be processing a large request.",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error from local model: {str(e)}",
            )

    async def stream_explanation(
        self, concept: str, learning_level: str, context: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream explanation word-by-word using cloud model.

        Args:
            concept: The concept to explain
            learning_level: The target learning level
            context: Optional additional context

        Yields:
            Chunks of the explanation
        """
        if not self._validate_cloud_client():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cloud API key is not configured.",
            )

        try:
            # Generate full explanation first
            explanation = await self.explain_with_cloud_model(
                concept, learning_level, context
            )

            # Stream word by word
            words = explanation.split()
            for i, word in enumerate(words):
                chunk = StreamChunk(
                    chunk=word,
                    chunk_index=i,
                    is_complete=i == len(words) - 1,
                )
                yield f"data: {chunk.model_dump_json()}\n\n"
                # Simulate streaming delay
                await asyncio.sleep(0.05)

            completion_chunk = StreamChunk(
                chunk="",
                chunk_index=len(words),
                is_complete=True,
            )
            yield f"event: done\ndata: {completion_chunk.model_dump_json()}\n\n"

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error during streaming: {str(e)}",
            )


# Initialize tutor
tutor = TutorAI()


# Explain endpoint (Cloud Model)
@app.post(
    "/explain",
    summary="Get Concept Explanation",
    description="Use the cloud model (Gemini via OpenAI-compatible API) to return a factual explanation.",
    response_model=ExplanationResponse,
    tags=["Explanations"],
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Invalid input payload.",
            "content": {
                "application/json": {
                    "example": {
                        "error": "ValidationError",
                        "detail": "[{'type': 'string_too_short', 'loc': ['body', 'concept'], 'msg': 'String should have at least 1 character'}]",
                        "status_code": 400,
                        "timestamp": "2026-04-15T10:30:00",
                    }
                }
            },
        },
        401: {
            "model": ErrorResponse,
            "description": "Cloud API key missing or invalid.",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Unauthorized",
                        "detail": "Cloud API key is not configured. Please set OPENAI_API_KEY in .env file.",
                        "status_code": 401,
                        "timestamp": "2026-04-15T10:30:00",
                    }
                }
            },
        },
        429: {
            "model": RateLimitError,
            "description": "Rate limit exceeded.",
            "content": {
                "application/json": {
                    "example": {
                        "error": "RateLimitExceeded",
                        "detail": "3 per 1 minute",
                        "status_code": 429,
                        "timestamp": "2026-04-15T10:30:00",
                        "retry_after": 60,
                    }
                }
            },
        },
        503: {
            "model": ErrorResponse,
            "description": "Cloud service unavailable.",
        },
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "concept": "Photosynthesis",
                        "learning_level": "beginner",
                        "context": "I am preparing for my biology test.",
                    }
                }
            }
        }
    },
)
@limiter.limit(f"{RATE_LIMIT}/minute")
async def explain_concept(
    request: Request, concept_request: ConceptRequest
) -> ExplanationResponse:
    """Return a factual explanation from the cloud model for a requested concept."""
    try:
        explanation = await tutor.explain_with_cloud_model(
            concept=concept_request.concept,
            learning_level=concept_request.learning_level,
            context=concept_request.context,
        )

        return ExplanationResponse(
            concept=concept_request.concept,
            explanation=explanation,
            learning_level=concept_request.learning_level,
            timestamp=datetime.now(),
            model_used=CLOUD_MODEL,
            tokens_used=len(explanation.split()),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


# Personalize endpoint (Local Model)
@app.post(
    "/personalize",
    summary="Get Personalized Explanation",
    description="Use the local Ollama model to create a creative and personalized explanation.",
    response_model=PersonalizedResponse,
    tags=["Personalization"],
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Invalid input payload.",
        },
        429: {
            "model": RateLimitError,
            "description": "Rate limit exceeded.",
        },
        503: {
            "model": ErrorResponse,
            "description": "Ollama unavailable or misconfigured.",
        },
        504: {
            "model": ErrorResponse,
            "description": "Local model timed out.",
        },
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "concept": "Binary Search",
                        "learning_level": "beginner",
                        "context": "I like explanations with gaming analogies.",
                    }
                }
            }
        }
    },
)
@limiter.limit(f"{RATE_LIMIT}/minute")
async def personalize_explanation(
    request: Request, concept_request: ConceptRequest
) -> PersonalizedResponse:
    """Get a creative, personalized explanation using the local model (Ollama/Llama)."""
    try:
        personalized = await tutor.personalize_with_local_model(
            concept=concept_request.concept,
            context=concept_request.context,
        )

        return PersonalizedResponse(
            concept=concept_request.concept,
            personalized_explanation=personalized,
            style="creative",
            timestamp=datetime.now(),
            model_used=f"{OLLAMA_MODEL} (local)",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


# Streaming endpoint
@app.post(
    "/explain/stream",
    summary="Stream Concept Explanation",
    description="Stream a concept explanation as SSE chunks in real time.",
    tags=["Streaming"],
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Cloud API key missing or invalid.",
        },
        429: {
            "model": RateLimitError,
            "description": "Rate limit exceeded.",
        },
        503: {
            "model": ErrorResponse,
            "description": "Cloud service unavailable.",
        },
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "concept": "Gradient Descent",
                        "learning_level": "intermediate",
                        "context": "I understand basic calculus.",
                    }
                }
            }
        }
    },
)
@limiter.limit(f"{RATE_LIMIT}/minute")
async def stream_explanation_endpoint(
    request: Request, concept_request: ConceptRequest
) -> StreamingResponse:
    """Stream a concept explanation in real-time using Server-Sent Events (SSE)."""
    try:
        return StreamingResponse(
            tutor.stream_explanation(
                concept=concept_request.concept,
                learning_level=concept_request.learning_level,
                context=concept_request.context,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming error: {str(e)}",
        )


def main():
    """Main entry point for the application."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info",
    )


if __name__ == "__main__":
    main()

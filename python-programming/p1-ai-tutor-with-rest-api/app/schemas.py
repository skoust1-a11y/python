from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ConceptRequest(BaseModel):
    """Input payload for requesting explanations from cloud or local models."""

    concept: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The concept/topic to explain.",
        examples=["Photosynthesis"],
    )
    learning_level: Literal["beginner", "intermediate", "advanced"] = Field(
        default="beginner",
        description="Difficulty level for the explanation.",
        examples=["beginner"],
    )
    context: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional learner context for personalization.",
        examples=["I learn best with analogies related to sports."],
    )


class ExplanationResponse(BaseModel):
    """Structured response for factual cloud-model explanations."""

    concept: str
    explanation: str
    learning_level: str
    timestamp: datetime
    model_used: str
    tokens_used: Optional[int] = None


class PersonalizedResponse(BaseModel):
    """Structured response for creative local-model explanations."""

    concept: str
    personalized_explanation: str
    style: str
    timestamp: datetime
    model_used: str


class StreamChunk(BaseModel):
    """A single server-sent chunk for streaming explanation output."""

    chunk: str
    chunk_index: int
    is_complete: bool


class ErrorResponse(BaseModel):
    """Standard error payload used across endpoints."""

    error: str
    detail: str
    status_code: int
    timestamp: datetime


class RateLimitError(ErrorResponse):
    """Specialized error payload for throttled requests."""

    retry_after: int

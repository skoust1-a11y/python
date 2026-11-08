

from pydantic import BaseModel, Field


class ConceptRequest(BaseModel):
    """Request payload for concept explanation endpoints."""

    concept: str = Field(..., description="Agentic AI concept to explain", example="RAG")


class ExplanationResponse(BaseModel):
    """Successful explanation response model."""

    concept: str = Field(..., description="The concept explained")
    explanation: str = Field(..., description="The generated explanation")
    model: str = Field(..., description="AI model used")


class ErrorResponse(BaseModel):
    """Standardized error response shape for API failures."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")

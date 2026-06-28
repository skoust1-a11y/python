"""Pydantic models for routing decisions."""

from pydantic import BaseModel, Field


class RoutingResult(BaseModel):
    """LLM routing decision returned as JSON."""

    route: str = Field(..., description="Selected route name (e.g. rag, sql, hybrid)")
    reason: str = Field(..., description="Brief justification for the routing choice")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Classifier confidence score (0–1)",
    )

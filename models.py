from pydantic import BaseModel, Field
from typing import Optional


class ResumeRequest(BaseModel):
    """Request model for resume screening."""
    candidate_name: str
    resume_text: str
    applying_for: str


class ResumeResponse(BaseModel):
    """Response model for resume screening."""
    success: bool
    candidate_name: str
    classified_role: str
    evaluator: str
    feedback: str


class ResumeFlowState(BaseModel):
    # REQUIRED - populated from the API request once the flow is kicked off.
    # NOTE: must have defaults - CrewAI instantiates the state class with no
    # arguments when the Flow is created, before kickoff(inputs=...) runs.
    candidate_name: str = ""
    resume_text: str = ""

    # OPTIONAL - User can provide or defaults to None
    applying_for: Optional[str] = Field(default=None)

    # AUTO-FILLED BY FLOW - Start as None
    classified_role: Optional[str] = Field(default=None)
    feedback: Optional[str] = Field(default=None)
    evaluator: Optional[str] = Field(default=None)

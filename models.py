from pydantic import BaseModel, Field
from typing import Optional

# TODO: Step 1 - Define ResumeFlowState BaseModel
# Hint: This model holds the internal state of the flow (inputs and outputs).
class ResumeFlowState(BaseModel):
    """Flow state model for resume screening."""
    # TODO: Add state fields
    # Hint: candidate_name, resume_text, applying_for, classified_role, justification, evaluator_role
    pass

# TODO: Step 2 - Define ResumeRequest BaseModel
# Hint: This is the input payload for the API endpoint.
class ResumeRequest(BaseModel):
    """Request model for resume screening."""
    # TODO: Add request fields
    # Hint: candidate_name, resume_text, applying_for (all strings)
    pass

# TODO: Step 3 - Define ResumeResponse BaseModel
# Hint: This is the structured response returned by the API.
class ResumeResponse(BaseModel):
    """Response model for resume screening."""
    # TODO: Add response fields
    # Hint: success, candidate_name, classified_role, evaluator, feedback
    pass

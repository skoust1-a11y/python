from pydantic import BaseModel, Field


# TODO: Step 1 - Define ExpensePolicyRequest BaseModel
# Hint: Use BaseModel with fields for expense_type, amount, policy_limit, receipt_provided, business_purpose.
class ExpensePolicyRequest(BaseModel):
    """Request model for expense policy validation."""
    pass  # TODO: Add request fields with appropriate types and descriptions


class ExpensePolicyResponse(BaseModel):
    """Response model for expense policy validation."""
    # TODO: Step 2 - Define response fields
    # Hint: Include success flag, decision text, and message string.
    pass  # TODO: Add success, decision, and message fields


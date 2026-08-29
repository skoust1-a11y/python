from pydantic import BaseModel, Field


# TODO: Step 1 - Define ExpensePolicyRequest BaseModel
# Hint: Use BaseModel with fields for expense_type, amount, policy_limit, receipt_provided, business_purpose.
class ExpensePolicyRequest(BaseModel):
    """Request model for expense policy validation."""
    expense_type: str = Field(..., description="Type of expense category (e.g., Travel, Meals, Software)")
    amount: int = Field(..., description="Amount claimed for reimbursement in dollars")
    policy_limit: int = Field(..., description="Maximum allowable policy limit for this category in dollars")
    receipt_provided: str = Field(..., description="Indication if a valid receipt is provided (e.g., 'yes' or 'no')")
    business_purpose: str = Field(..., description="Business justification and purpose for the expense")


class ExpensePolicyResponse(BaseModel):
    """Response model for expense policy validation."""
    # TODO: Step 2 - Define response fields
    # Hint: Include success flag, decision text, and message string.
    success: bool = Field(..., description="Indicates if the validation operation completed successfully")
    decision: str = Field(..., description="Detailed decision and policy compliance analysis from the crew")
    message: str = Field(..., description="Summary or status message regarding the validation execution")



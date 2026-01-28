from fastapi import FastAPI, HTTPException

from models import ExpensePolicyRequest, ExpensePolicyResponse
from services import validate_expense_policy


app = FastAPI(
    title="Expense Policy Validator API",
    description="API for validating an expense claim against a simple company policy using a hierarchical CrewAI crew",
    version="1.0.0",
)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Expense Policy Validator API",
        "version": "1.0.0",
        "endpoints": {
            "POST /expense/validate": "Validate an expense claim against policy",
            "GET /health": "Health check endpoint",
        },
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "expense-policy-validator"}


@app.post("/expense/validate", response_model=ExpensePolicyResponse)
async def validate_expense(request: ExpensePolicyRequest):
    """
    Validate an expense claim against policy using the hierarchical crew.

    TODOs:
    1. Add minimal request validation for the required fields.
    2. Call the service layer function to run the crew and get the decision text.
    3. Map successful decisions into an ExpensePolicyResponse.
    4. Convert service-level errors into HTTPException responses.

    """
    # TODO: Step 1 - Validate basic request fields
    # Hint: Ensure no required field is empty before calling the service.

    # TODO: Step 2 - Delegate to the service
    # Hint: Call validate_expense_policy with the request model.

    # TODO: Step 3 - Return a successful response
    # Hint: Wrap the decision string in an ExpensePolicyResponse with success=True.

    # TODO: Step 4 - Handle errors
    # Hint: Convert ValueError to a 400 response and other errors to a 500 response.

    raise NotImplementedError("This route is not yet implemented. Please complete the TODO steps above.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Loan Application Assessment API",
    description="Multi-Agent Loan Application Assessment System using LangGraph",
    version="1.0"
)

# TODO: Build graph using build_graph() function
# graph = build_graph()


class LoanApplicationRequest(BaseModel):
    """
    Request model for loan application assessment.
    
    TODO:
    1. Define loan_purpose: str field
    2. Define credit_score: int = 0 field
    3. Define monthly_income: float = 0 field
    4. Define property_value: float = 0 field
    5. Define property_address: str = "" field
    6. Define vehicle_make: str = "" field
    7. Define vehicle_model: str = "" field
    8. Define vehicle_value: float = 0 field
    """
    # TODO: Implement LoanApplicationRequest fields
    pass


@app.post("/assess-loan")
def assess_loan(request: LoanApplicationRequest):
    """
    Assess a loan application using the multi-agent workflow.
    
    TODO:
    1. Initialize state dict with:
       - loan_type: ""
       - applicant_info: dict containing all fields from request
       - findings: []
       - final_decision: ""
    2. Invoke graph with initial state
    3. Deduplicate findings in response (workaround for state merge)
    4. Return dict with loan_type, findings (deduplicated), and final_decision
    """
    # TODO: Implement assess_loan endpoint logic
    return {}


if __name__ == "__main__":
    # TODO: Add uvicorn.run() to start the server
    pass

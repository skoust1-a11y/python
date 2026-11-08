from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from graph.build_graph import build_graph

app = FastAPI(
    title="Loan Application Assessment API",
    description="Multi-Agent Loan Application Assessment System using LangGraph",
    version="1.0"
)

_graph = None

def building():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


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
    loan_purpose: str
    credit_score: int = 0
    monthly_income: float = 0
    property_value: float = 0
    property_address: str = ""
    vehicle_make: str = ""
    vehicle_model: str = ""
    vehicle_value: float = 0


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
    state = {
        "loan_type": "",
        "applicant_info": request.model_dump(),
        "findings": [],
        "final_decision": "",
    }

    graph = building()
    response = graph.invoke(state)

    findings = response.get("findings", []) or []
    deduplicated_findings = list(dict.fromkeys(findings))

    return {
        "loan_type": response.get("loan_type", state["loan_type"]),
        "findings": deduplicated_findings,
        "final_decision": response.get("final_decision", ""),
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

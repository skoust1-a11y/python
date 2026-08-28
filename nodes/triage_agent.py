from ..config.config import config
from langchain_core.prompts import PromptTemplate
from ..config.llms import get_llm

def triage_agent(state):
    """
    LLM-based triage agent that determines the loan type based on application details.
    """
    loan_purpose = str(
        state.get("applicant_info", {}).get("loan_purpose", "")
    ).strip()

    prompt = PromptTemplate(
        template=(
            "You are a loan triage assistant. Classify the loan purpose into exactly one of: "
            "home, personal, or auto.\n"
            "Loan purpose: {loan_purpose}\n"
            "Respond with only one word."
        ),
        input_variables=["loan_purpose"],
    )


    try:
        response = get_llm().invoke(prompt.format(loan_purpose=loan_purpose)).strip().lower()
        valid_classifications = {"home", "personal", "auto"}
        classification = next(
            (item for item in valid_classifications if item in response),
            None,
        )
    except Exception:
        classification = None

    if not classification:
        if "home" in loan_purpose.lower():
            classification = "home"
        elif "auto" in loan_purpose.lower() or "vehicle" in loan_purpose.lower():
            classification = "auto"
        elif "personal" in loan_purpose.lower():
            classification = "personal"
        else:
            classification = "personal"

    state["loan_type"] = classification
    return state

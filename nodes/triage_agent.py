def triage_agent(state):
    """
    LLM-based triage agent that determines the loan type based on application details.
    
    TODO:
    1. Get loan_purpose from state["applicant_info"]
    2. Use Azure OpenAI LLM to classify loan type (home, personal, or auto)
    3. Validate LLM response - ensure it's one of: "home", "personal", "auto"
    4. Default to "personal" if response is invalid
    5. Update state["loan_type"] with the classified type
    6. Return updated state
    """
    # TODO: Implement triage_agent logic
    return {}

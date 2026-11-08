def credit_score_reviewer(state):
    """
    Checks applicant's credit profile and repayment history.
    This node runs in parallel with property_assessor for home loans.
    
    TODO:
    1. Get credit_score from state["applicant_info"]
    2. Analyze credit score and create an appropriate finding message
    3. Return {"findings": [finding]} format
    Note: This runs in parallel with property_assessor for home loans
    """
    # TODO: Implement credit_score_reviewer logic
    applicant_info = state.get("applicant_info", {})
    credit_score = applicant_info.get("credit_score", 0)

    findings = []

    if credit_score <= 0:
        findings.append(
            "Credit score is missing or invalid for review."
        )
    elif credit_score < 600:
        findings.append(
            "Credit score is poor; loan approval is unlikely without stronger compensating factors."
        )
    elif credit_score < 700:
        findings.append(
            "Credit score is fair; approval may depend on loan type and applicant income."
        )
    elif credit_score < 750:
        findings.append(
            "Credit score is good; the applicant is likely eligible for many loan options."
        )
    else:
        findings.append(
            "Credit score is excellent; the applicant should qualify for competitive loan terms."
        )

    return {"findings": findings}

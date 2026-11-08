def personal_loan_reviewer(state):
    """
    Independently reviews credit and income details for personal loans.
    
    TODO:
    1. Get monthly_income and credit_score from state["applicant_info"]
    2. Review both income and credit score
    3. Create multiple findings based on the review
    4. Return {"findings": [finding1, finding2, ...]} format
    Note: This runs independently (not in parallel with other nodes)
    """
    # TODO: Implement personal_loan_reviewer logic
    findings = []
    applicant_info = state.get("applicant_info", {})
    
    monthly_income = applicant_info.get("monthly_income", 0)
    credit_score = applicant_info.get("credit_score", 0)
    
    # Review income
    if monthly_income <= 0:
        findings.append(
            "Monthly income is missing or invalid for review."
        )
    elif monthly_income < 2000:
        findings.append(
            "Monthly income is low; personal loan approval may be challenging."
        )
    elif monthly_income < 5000:
        findings.append(
            "Monthly income is moderate; applicant may qualify for standard personal loans."
        )
    else:
        findings.append(
            "Monthly income is strong; applicant is likely eligible for higher loan amounts."
        )
    
    # Review credit score
    if credit_score <= 0:
        findings.append(
            "Credit score is missing or invalid for review."
        )
    elif credit_score < 600:
        findings.append(
            "Credit score is poor; personal loan approval is unlikely without compensating factors."
        )
    elif credit_score < 700:
        findings.append(
            "Credit score is fair; approval depends on income and other factors."
        )
    else:
        findings.append(
            "Credit score is good or excellent; applicant is eligible for competitive personal loan terms."
        )
    
    return {"findings": findings}

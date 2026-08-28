def property_assessor(state):
    """
    Validates property documents and market valuation.
    This node runs in parallel with credit_score_reviewer for home loans.
    
    TODO:
    1. Get property_value and property_address from state["applicant_info"]
    2. Create a finding message about property validation
    3. Return {"findings": [finding]} format
    Note: This runs in parallel with credit_score_reviewer for home loans
    """
    application = state.get("applicant_info", {}) or {}
    property_value = application.get('property_value')
    property_address = application.get('property_address')

    findings = []

    if not property_address or not isinstance(property_address, str) or property_address.strip() == "":
        findings.append("Invalid property_address")
    else:
        findings.append("Valid Property Address")

    if property_value is None:
        findings.append("Invalid property_value: missing")
    else:
        try:
            val = float(property_value)
            if val <= 0:
                findings.append("Invalid property_value: must be > 0")
            else:
                findings.append("Valid Property Value")
        except Exception:
            findings.append("Invalid property_value: not a number")

    return {"findings": findings}

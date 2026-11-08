def auto_loan_reviewer(state):
    """
    Independently validates vehicle details and loan eligibility for auto loans.
    
    TODO:
    1. Get vehicle_make, vehicle_model, vehicle_value from state["applicant_info"]
    2. Validate vehicle details
    3. Create findings about vehicle validation and loan eligibility
    4. Return {"findings": [finding1, finding2, ...]} format
    Note: This runs independently (not in parallel with other nodes)
    """
    # TODO: Implement auto_loan_reviewer logic
    applicant_info = state["applicant_info"]
    vehicle_make = applicant_info.get("vehicle_make", "").strip()
    vehicle_model = applicant_info.get("vehicle_model", "").strip()
    vehicle_value = applicant_info.get("vehicle_value", 0)

    findings = []

    if not vehicle_make or not vehicle_model:
        findings.append(
            "Vehicle make and model must be provided for auto loan review."
        )
    else:
        findings.append(
            f"Vehicle details received: {vehicle_make} {vehicle_model}."
        )

    if vehicle_value <= 0:
        findings.append(
            "Vehicle value must be greater than 0 to assess auto loan eligibility."
        )
    elif vehicle_value < 5000:
        findings.append(
            "Vehicle value is low; auto loan approval may be more difficult."
        )
    else:
        findings.append(
            "Vehicle value is sufficient for auto loan consideration."
        )

    return {"findings": findings}

def final_aggregator(state):
    """
    Aggregates results from all reviewer agents into a consolidated loan decision report.
    This node runs after all parallel branches complete (fan-in/join pattern).
    
    TODO:
    1. Get findings list from state
    2. Optionally deduplicate findings (workaround for state merge edge cases)
    3. Create a formatted decision report with:
       - Loan type
       - Total findings count
       - List of all findings
    4. Update state["final_decision"] with the formatted report
    5. Return updated state
    """
    findings = state.get("findings", []) or []
    if not isinstance(findings, list):
        findings = [findings]

    unique_findings = list(dict.fromkeys(findings))
    loan_type = state.get("loan_type", "unknown")

    report_lines = [
        f"Loan Type: {loan_type}",
        f"Total Findings: {len(unique_findings)}",
        "Findings:",
    ]
    report_lines.extend(f"- {finding}" for finding in unique_findings)

    state["findings"] = unique_findings
    state["final_decision"] = "\n".join(report_lines)
    return state

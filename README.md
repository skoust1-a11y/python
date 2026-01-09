# Multi-Agent Loan Application Assessment System

## Project Context

You're building a Multi-Agent Loan Application Assessment System, an AI-powered workflow that processes loan applications through specialized reviewer agents. The system uses LLM-based triage to classify loan types and routes applications to appropriate reviewers, with parallel processing for complex assessments.

This practice focuses on building multi-agent workflows with LangGraph — implementing conditional routing (LO1) and parallel execution (LO2). You'll learn how to create state schemas with reducers for parallel state merging, build graph nodes that process loan applications, implement conditional routing based on state, and execute parallel tasks using fork-join patterns.

## Problem Statement

Build a multi-agent loan application assessment workflow using LangGraph with conditional routing and parallel execution capabilities. The system must support LLM-based loan type classification, route to specialized reviewer agents based on loan type, execute parallel reviews for home loans, and aggregate findings into a final decision report. You need to implement state schemas with parallel state merging, graph nodes for different loan reviewers, conditional routing functions, and FastAPI endpoints that process loan applications.

You will complete multiple implementation tasks to build this assessment system:

## Task 1 — Define State Schema

### Goal

Build the foundational data structure for state management with support for parallel state merging.

### Requirements

1. mport TypedDict, Annotated, and operator
2. Define LoanApplicationState with loan_type, applicant_info, mergeable findings, and final_decision

**File:** `state/loan_state.py`

## Task 2 — Implement Triage Agent

### Goal

Build an LLM-based agent that classifies loan applications into different types.

### Requirements

1. Create get_llm() for AzureChatOpenAI
2. Error if env vars missing
3. Classify loan_purpose → home/personal/auto, validate, update state

**File:** `nodes/triage_agent.py`

## Task 3 — Implement Routing Function

### Goal

Build a routing function that determines the next node based on loan type classification.

### Requirements

1. Read loan_type and route to correct reviewer
2. Return valid conditional edge key

**File:** `routing/route_loan_type.py`

## Task 4 — Implement Reviewer Nodes

### Goal

Build specialized reviewer nodes that process different loan types and return findings.

### Requirements

1. Home reviewer: pass-through
2. Credit reviewer: analyze credit score → findings
3. Property assessor: validate property → findings
4. Personal reviewer: income + credit → findings
5. Auto reviewer: vehicle details → findings

**Files:** `nodes/home_loan_reviewer.py`, `nodes/credit_score_reviewer.py`, `nodes/property_assessor.py`, `nodes/personal_loan_reviewer.py`, `nodes/auto_loan_reviewer.py`

## Task 5 — Implement Final Aggregator

### Goal

Build an aggregator node that combines all findings into a final decision report.

### Requirements

1. Collect and deduplicate findings
2. Build final decision report and update state

**File:** `nodes/final_aggregator.py`

## Task 6 — Implement Graph Construction

### Goal

Build the LangGraph workflow with conditional routing and parallel execution.

### Requirements

1. Register all nodes in StateGraph
2. Add conditional routing and parallel edges
3. Fan-in to final aggregator and END

**File:** `graph/build_graph.py`

## Task 7 — Implement FastAPI Endpoint

### Goal

Build REST API endpoint that processes loan applications and returns assessment results.

### Requirements

1. Define request model
2. Initialize state and invoke graph
3. Return loan_type, findings, final_decision

**File:** `main.py`

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. **State Schema Definition**: LoanApplicationState TypedDict is defined with loan_type (str), applicant_info (dict), findings (Annotated[list, operator.add]), and final_decision (str) fields. The findings field uses operator.add reducer for parallel state merging. All imports (TypedDict, Annotated, operator) are correctly included.

2. **Triage Agent Implementation**: triage_agent function has correct signature accepting state parameter. get_llm() helper function retrieves Azure OpenAI credentials from environment variables and raises ValueError if not configured. Function extracts loan_purpose from applicant_info, invokes LLM with classification prompt, validates response is one of ["home", "personal", "auto"], defaults to "personal" if invalid, updates state["loan_type"], and returns updated state. Function does not return None or empty dict.

3. **Routing Function Implementation**: route_loan_type function has correct signature accepting state parameter and returns str. Function gets loan_type from state and converts to lowercase. Returns "home_loan_reviewer" if "home" in loan_type, "personal_loan_reviewer" if "personal" in loan_type, "auto_loan_reviewer" if "auto" in loan_type, and "final_aggregator" as default fallback. Return values match keys in conditional edges mapping.

4. **Home Loan Reviewer Implementation**: home_loan_reviewer function has correct signature accepting state parameter. Function acts as pass-through coordinator and returns state unchanged. Function does not return None.

5. **Credit Score Reviewer Implementation**: credit_score_reviewer function has correct signature accepting state parameter. Function gets credit_score from state["applicant_info"], analyzes credit score and creates appropriate finding message, and returns {"findings": [finding]} format. Function does not return None or empty dict.

6. **Property Assessor Implementation**: property_assessor function has correct signature accepting state parameter. Function gets property_value and property_address from state["applicant_info"], creates finding message about property validation, and returns {"findings": [finding]} format. Function does not return None or empty dict.

7. **Personal Loan Reviewer Implementation**: personal_loan_reviewer function has correct signature accepting state parameter. Function gets monthly_income and credit_score from state["applicant_info"], reviews both and creates multiple findings, and returns {"findings": [finding1, finding2, ...]} format. Function does not return None or empty dict.

8. **Auto Loan Reviewer Implementation**: auto_loan_reviewer function has correct signature accepting state parameter. Function gets vehicle_make, vehicle_model, vehicle_value from state["applicant_info"], validates vehicle details and creates findings, and returns {"findings": [finding1, finding2, ...]} format. Function does not return None or empty dict.

9. **Final Aggregator Implementation**: final_aggregator function has correct signature accepting state parameter. Function gets findings list from state, optionally deduplicates findings, creates formatted decision report with loan type, total findings count, and numbered list of findings, updates state["final_decision"] with formatted report, and returns updated state. Function does not return None.

10. **Graph Construction Implementation**: build_graph function imports all necessary modules (StateGraph, END, state, nodes, routing). Creates StateGraph with LoanApplicationState schema. Registers all seven nodes using add_node. Sets entry point to "triage_agent" using set_entry_point. Adds conditional edges from "triage_agent" using add_conditional_edges with route_loan_type function and proper mapping. For home loans: adds separate edges from "home_loan_reviewer" to "credit_score_reviewer" and "property_assessor" (fan-out using separate add_edge calls, not list syntax for end_key). Adds edge from ["credit_score_reviewer", "property_assessor"] to "final_aggregator" (fan-in using list syntax for start_key). Adds edges from "personal_loan_reviewer" and "auto_loan_reviewer" directly to "final_aggregator". Adds edge from "final_aggregator" to END. Returns compiled graph using builder.compile(). Function does not return None.

11. **FastAPI Application Implementation**: FastAPI app is created with title, description, and version. Graph is built using build_graph() at module level. LoanApplicationRequest Pydantic model is defined with all required fields (loan_purpose, credit_score, monthly_income, property_value, property_address, vehicle_make, vehicle_model, vehicle_value) with correct types and default values.

12. **POST /assess-loan Endpoint Implementation**: POST /assess-loan endpoint is decorated with @app.post("/assess-loan") and accepts LoanApplicationRequest parameter. Endpoint initializes state dict with loan_type (""), applicant_info (dict with all request fields), findings ([]), and final_decision (""). Invokes graph with initial state using graph.invoke(initial_state). Deduplicates findings in response using key-based deduplication. Returns dict with loan_type, findings (deduplicated), and final_decision. Endpoint handles exceptions gracefully.



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

1. Import `TypedDict`, `Annotated` from `typing` and `operator` module
2. Define `LoanApplicationState` TypedDict with:
   - `loan_type: str` - The classified loan type (home, personal, or auto)
   - `applicant_info: dict` - Contains loan_purpose and other applicant details
   - `findings: Annotated[list, operator.add]` - List that merges results from parallel agents (critical for parallel execution)
   - `final_decision: str` - Final consolidated decision report

**File:** `state/loan_state.py`

## Task 2 — Implement Triage Agent

### Goal

Build an LLM-based agent that classifies loan applications into different types.

### Requirements

1. Implement `get_llm()` helper function to get AzureChatOpenAI instance from environment variables
2. Raise ValueError if Azure OpenAI environment variables are not configured
3. Implement `triage_agent(state)` function that:
   - Extracts `loan_purpose` from `state["applicant_info"]`
   - Uses Azure OpenAI LLM to classify loan type (home, personal, or auto)
   - Validates LLM response - ensures it's one of: "home", "personal", "auto"
   - Defaults to "personal" if response is invalid
   - Updates `state["loan_type"]` with the classified type
   - Returns updated state

**File:** `nodes/triage_agent.py`

## Task 3 — Implement Routing Function

### Goal

Build a routing function that determines the next node based on loan type classification.

### Requirements

1. Implement `route_loan_type(state)` function that:
   - Gets `loan_type` from state (convert to lowercase)
   - Returns "home_loan_reviewer" if "home" in loan_type
   - Returns "personal_loan_reviewer" if "personal" in loan_type
   - Returns "auto_loan_reviewer" if "auto" in loan_type
   - Returns "final_aggregator" as default fallback
2. Function must return a string that matches a key in the conditional edges mapping

**File:** `routing/route_loan_type.py`

## Task 4 — Implement Reviewer Nodes

### Goal

Build specialized reviewer nodes that process different loan types and return findings.

### Requirements

1. Implement `home_loan_reviewer(state)` - Pass-through coordinator that returns state unchanged
2. Implement `credit_score_reviewer(state)` that:
   - Gets `credit_score` from `state["applicant_info"]`
   - Analyzes credit score and creates an appropriate finding message
   - Returns `{"findings": [finding]}` format
3. Implement `property_assessor(state)` that:
   - Gets `property_value` and `property_address` from `state["applicant_info"]`
   - Creates a finding message about property validation
   - Returns `{"findings": [finding]}` format
4. Implement `personal_loan_reviewer(state)` that:
   - Gets `monthly_income` and `credit_score` from `state["applicant_info"]`
   - Reviews both income and credit score
   - Creates multiple findings based on the review
   - Returns `{"findings": [finding1, finding2, ...]}` format
5. Implement `auto_loan_reviewer(state)` that:
   - Gets `vehicle_make`, `vehicle_model`, `vehicle_value` from `state["applicant_info"]`
   - Validates vehicle details
   - Creates findings about vehicle validation and loan eligibility
   - Returns `{"findings": [finding1, finding2, ...]}` format

**Files:** `nodes/home_loan_reviewer.py`, `nodes/credit_score_reviewer.py`, `nodes/property_assessor.py`, `nodes/personal_loan_reviewer.py`, `nodes/auto_loan_reviewer.py`

## Task 5 — Implement Final Aggregator

### Goal

Build an aggregator node that combines all findings into a final decision report.

### Requirements

1. Implement `final_aggregator(state)` function that:
   - Gets `findings` list from state
   - Optionally deduplicates findings (workaround for state merge edge cases)
   - Creates a formatted decision report with:
     - Loan type
     - Total findings count
     - List of all findings (numbered)
   - Updates `state["final_decision"]` with the formatted report
   - Returns updated state

**File:** `nodes/final_aggregator.py`

## Task 6 — Implement Graph Construction

### Goal

Build the LangGraph workflow with conditional routing and parallel execution.

### Requirements

1. Import all necessary modules: `StateGraph`, `END` from `langgraph.graph`, state, nodes, routing
2. Create `StateGraph` with `LoanApplicationState`
3. Register all nodes using `add_node`: triage_agent, home_loan_reviewer, credit_score_reviewer, property_assessor, personal_loan_reviewer, auto_loan_reviewer, final_aggregator
4. Set entry point to "triage_agent" using `set_entry_point`
5. Add conditional edges from "triage_agent" using `add_conditional_edges` with `route_loan_type` function
6. For home loans: add separate edges from "home_loan_reviewer" to "credit_score_reviewer" and "property_assessor" (fan-out - use separate `add_edge` calls)
7. Add edge from `["credit_score_reviewer", "property_assessor"]` to "final_aggregator" (fan-in - use list syntax for start_key)
8. Add edges from "personal_loan_reviewer" and "auto_loan_reviewer" directly to "final_aggregator"
9. Add edge from "final_aggregator" to `END`
10. Return compiled graph using `builder.compile()`

**File:** `graph/build_graph.py`

## Task 7 — Implement FastAPI Endpoint

### Goal

Build REST API endpoint that processes loan applications and returns assessment results.

### Requirements

1. Create FastAPI app instance with title, description, version
2. Build graph using `build_graph()` function (call at module level)
3. Define `LoanApplicationRequest` Pydantic model with fields:
   - `loan_purpose: str`
   - `credit_score: int = 0`
   - `monthly_income: float = 0`
   - `property_value: float = 0`
   - `property_address: str = ""`
   - `vehicle_make: str = ""`
   - `vehicle_model: str = ""`
   - `vehicle_value: float = 0`
4. Implement `POST /assess-loan` endpoint that:
   - Accepts `LoanApplicationRequest` parameter
   - Initializes state dict with:
     - `loan_type: ""`
     - `applicant_info: dict` containing all fields from request
     - `findings: []`
     - `final_decision: ""`
   - Invokes graph with initial state using `graph.invoke(initial_state)`
   - Deduplicates findings in response (workaround for state merge)
   - Returns dict with `loan_type`, `findings` (deduplicated), and `final_decision`
5. Add main block to run uvicorn server

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

13. **Main Block Implementation**: Main block includes uvicorn.run() to start the server with appropriate host, port, and reload settings.

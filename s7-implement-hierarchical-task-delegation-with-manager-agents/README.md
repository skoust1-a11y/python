# Expense Policy Validator

A FastAPI-based service that uses a hierarchical CrewAI crew to validate an expense claim against a simple company policy.

## Project Context

You are building an Expense Policy Validator Crew, an AI-powered system that uses a 3-agent hierarchical CrewAI crew to validate expense claims against a simple company policy and produce an auditable decision summary. The system uses manager-led autonomous collaboration where a Finance Manager coordinates two specialist agents (Policy Interpreter and Expense Validator) to interpret policy, apply decision logic, and produce a final decision with reasoning.

This practice focuses on building hierarchical crews with CrewAI — implementing a custom manager_agent with a clear role and goal, defining specialist agents with focused responsibilities, creating a single high-level task for the manager, assembling a hierarchical crew, and exposing the crew as a REST API. You will configure Azure OpenAI LLM for CrewAI, define the three agents, create a high-level validation task that includes policy and expense details, assemble the crew with Process.hierarchical, and implement FastAPI endpoints that accept expense details and return structured validation results.

## Problem Statement

Build an Expense Policy Validator crew that responds to expense claims by interpreting company policy, checking compliance, calculating any excess amount, and producing a final decision with reasoning. You need to implement Azure OpenAI LLM configuration, three agents (Policy Interpreter, Expense Validator, Finance Manager), a single high-level validation task, hierarchical crew assembly, Pydantic request/response models, and FastAPI endpoints that process validation requests and return structured results.

You will complete multiple implementation tasks to build this Expense Policy Validator crew:

## Task 1 — Implement Crew Service

### Goal

Build the complete CrewAI crew service with LLM initialization, three agents, one high-level task, and hierarchical crew assembly.

### Requirements

1. Load environment variables.
2. Read Azure OpenAI credentials from env.
3. Validate required env vars; raise `ValueError` if missing.
4. Initialize Azure OpenAI LLM.
5. Create Policy Interpreter agent.
6. Create Expense Validator agent.
7. Create Finance Manager manager_agent.
8. Create one high-level validation Task (policy + expense details, expected_output, `output_file="expense_decision.md"`).
9. Create hierarchical Crew with specialists, Task, and manager_agent.
10. Return crew execution result.

**File:** `services.py`

## Task 2 — Implement Pydantic Models

### Goal

Define request and response models for the FastAPI endpoint.

### Requirements

1. Import `BaseModel` and `Field`.
2. Define `ExpensePolicyRequest` fields: `expense_type`, `amount`, `policy_limit`, `receipt_provided`, `business_purpose`.
3. Define `ExpensePolicyResponse` fields: `success`, `decision`, `message`.

**File:** `models.py`

## Task 3 — Implement FastAPI Endpoint

### Goal

Build REST API endpoint that processes expense validation requests.

### Requirements

1. Import models and service function.
2. Implement `POST /expense/validate`.
3. Validate required fields.
4. Call the crew service and return `ExpensePolicyResponse`.
5. Handle errors with `HTTPException`.

**File:** `main.py`

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. **Crew Service Implementation**: `services.py` properly loads environment variables, validates Azure OpenAI credentials, initializes LLM with Azure configuration, defines three agents (Policy Interpreter, Expense Validator, Finance Manager), creates a single high-level Task with policy and expense details, assembles a hierarchical Crew with `Process.hierarchical` and `manager_agent`, and returns crew execution results.
2. **Pydantic Models Implementation**: `ExpensePolicyRequest` BaseModel is defined with all required fields and descriptions. `ExpensePolicyResponse` BaseModel is defined with success, decision, and message fields.
3. **FastAPI Endpoint Implementation**: `POST /expense/validate` validates that required fields are not empty, calls the crew service, handles exceptions with `HTTPException`, and returns `ExpensePolicyResponse` with the decision text and a success message.

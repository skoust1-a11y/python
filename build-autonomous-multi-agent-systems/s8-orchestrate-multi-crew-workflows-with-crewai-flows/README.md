# Resume Screening & Candidate Routing

A FastAPI-based service that uses a multi-crew orchestration system using CrewAI Flows to screen resumes, route them to specialized crews, and generate AI-driven hiring recommendations.

## Project Context

You are building a Resume Screening and Candidate Routing system, an AI-powered application that uses CrewAI Flows to orchestrate specialized evaluation crews based on resume content. The system uses a flow-based architecture where a main flow classifies a resume, routes it to the appropriate domain-specific crew (Data Analyst, HR, Sales, or General), and aggregates the evaluation results.

This practice focuses on building orchestrations with CrewAI Flows - implementing a `Flow` class with state management, using decorators like `@start`, `@router`, and `@listen` to define the workflow, creating specialized agents for different domains, and exposing the entire process as a REST API. You will configure Azure OpenAI LLM, define the flow state, implement the routing logic, and create a FastAPI application to serve the model.

## Problem Statement

Build a Resume Screening pipeline that accepts a candidate's name and resume text, classifies the role, routes it to the correct evaluator, and produces a structured assessment. You need to implement Azure OpenAI LLM configuration, the flow orchestration logic, Pydantic models for state and API communication, and a FastAPI endpoint.

You will complete multiple implementation tasks to build this Resume Screening Flow:

## Task 1 — Implement Crew Service

### Goal

Build the complete CrewAI Flow service with LLM initialization, classification logic, routing, and specialized evaluator execution.

### Requirements

1. Load environment variables.
2. Read Azure OpenAI credentials from env.
3. Validate required env vars.
4. Initialize Azure OpenAI LLM.
5. Define `ResumeScreeningFlow` class inheriting from `Flow`.
6. Implement `classify_resume` method decorated with `@start` to determine the role.
7. Implement `route_application` method decorated with `@router` to direct the flow.
8. Implement `_run_evaluator` helper to create and run specialized agents.
9. Implement listeners (e.g., `run_data_analyst_crew`) for each track.
10. Implement `process_resume` async wrapper to run the flow.

**File:** `services.py`

## Task 2 — Implement Pydantic Models

### Goal

Define the Flow State and request/response models for the FastAPI endpoint.

### Requirements

1. Import `BaseModel` and `Field`.
2. Define `ResumeFlowState` with fields like `candidate_name`, `resume_text`, `classified_role`, `justification`, etc.
3. Define `ResumeRequest` fields: `candidate_name`, `resume_text`, `applying_for`.
4. Define `ResumeResponse` fields: `success`, `candidate_name`, `classified_role`, `evaluator`, `feedback`.

**File:** `models.py`

## Task 3 — Implement FastAPI Endpoint

### Goal

Build REST API endpoint that processes resume screening requests.

### Requirements

1. Import models and service function.
2. Implement `POST /screen`.
3. Validate required fields.
4. Call `process_resume` and return `ResumeResponse`.
5. Handle errors with `HTTPException`.

**File:** `main.py`

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. **Crew Service Implementation**: `services.py` properly loads environment variables, initializes LLM, implements the `ResumeScreeningFlow` with correct `@start`, `@router`, and `@listen` decorators, and successfully routes resumes to different crews based on content.
2. **Pydantic Models Implementation**: `ResumeFlowState` correctly manages the flow's internal state. `ResumeRequest` and `ResumeResponse` are defined with appropriate fields and types.
3. **FastAPI Endpoint Implementation**: `POST /screen` acts as the entry point, accepting JSON requests, triggering the flow, and returning a structured JSON response with the AI's feedback.


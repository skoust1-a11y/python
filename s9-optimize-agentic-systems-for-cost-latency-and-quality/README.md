# Customer Support Ticket Optimization System

A FastAPI-based service that uses an intelligent **Gateway Router Pattern** to optimize support ticket resolution by routing queries to different model tiers (local Ollama vs. Azure OpenAI) based on complexity.

## Project Context

You are building a Customer Support Ticket Optimization System, an AI-powered application designed to balance cost, latency, and reasoning capabilities. The system uses a **Gateway Router** architecture where a heuristic-based router assesses the complexity of an incoming ticket description. 

If the ticket is classified as "Simple" (e.g., billing, account FAQs), it is routed to a local **Ollama (Llama 3.2)** model to save costs. If the ticket is classified as "Complex" (e.g., technical errors, bug reports), it is routed to a high-performance **Azure OpenAI (GPT-4o-mini)** model. All routing is abstracted through a **LiteLLM Gateway**.

This practice focuses on implementing logic for model tier selection, integrating with LiteLLM using the OpenAI client, and building a standardized FastAPI interface for support operations.

## Problem Statement

Build a support ticket resolution pipeline that accepts a problem description, determines the required reasoning power via heuristics, and fulfills the request using the most efficient model tier. You need to implement the heuristic routing logic, the FastAPI endpoint, and the LiteLLM client configuration.

You will complete multiple implementation tasks to build this Support Optimization System:

## Task 1 — Implement Heuristic Router

### Goal

Build the logic to assess ticket complexity without using an LLM, ensuring zero-latency categorization.

### Requirements

1. Implement the `assess_complexity` function in `router.py`.
2. Define keyword lists for **Complex** triggers (e.g., `500`, `error`, `bug`, `crash`, `deployment`, `api`).
3. Define keyword lists for **Simple** triggers (e.g., `billing`, `invoice`, `address`, `account`, `status`).
4. Implement a length-based heuristic where descriptions longer than 50 words are automatically routed to the **Complex** tier.
5. Ensure the function returns either `"complex"` or `"simple"`.

**File:** `router.py`

## Task 2 — Implement FastAPI Gateway

### Goal

Build the REST API and the gateway orchestration logic using LiteLLM.

### Requirements

1. Initialize the `OpenAI` client pointing to the LiteLLM Gateway URL (`http://localhost:4000/v1`).
2. Define the `TicketRequest` Pydantic model with a single `description` field.
3. Implement the `POST /resolve` endpoint.
4. Inside the endpoint:
    - Call the `assess_complexity` function.
    - Set the `model` parameter based on the assessment (`complex-agent` vs `simple-agent`).
    - Call the LiteLLM gateway using the client.
    - Return a JSON response containing the `complexity_assessment`, `routed_model_tier`, and the `resolution`.

**File:** `main.py`

## Task 3 - Configure LiteLLM Gateway

### Goal

Configure the proxy to route to the correct local and cloud backends.

### Requirements

1. Define a `simple-agent` entry in `litellm_config.yaml` using `ollama/llama3.2`.
2. Define a `complex-agent` entry in `litellm_config.yaml` using `azure/gpt-4o-mini`.
3. Use environment variables for all sensitive Azure credentials.

**File:** `litellm_config.yaml`

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. **Heuristic Accuracy**: `router.py` correctly distinguishes between technical/complex logs and simple billing/account queries.
2. **Gateway Logic**: `main.py` successfully uses the OpenAI client to communicate with LiteLLM and routes to the correct model tier based on the router's output.
3. **API Integrity**: The `POST /resolve` endpoint validates input correctly and returns a structured response that matches the expected format in the documentation.
4. **Performance Optimization**: Simple requests are successfully fulfilled by the local model tier (verifiable via LiteLLM logs), while complex requests leverage cloud reasoning.

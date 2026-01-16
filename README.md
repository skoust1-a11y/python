# Market Research Agent 

## Project Context

You're building a Market Research Agent, an AI-powered system that conducts market research by gathering real data from the web, performing analysis, and generating insights. The system uses a Plan-Act-Check pattern to generate upfront execution plans, execute steps systematically, verify each step's success, and replan when failures occur.

This practice focuses on building Plan-Act-Check agents with LangGraph — implementing planning nodes that decompose tasks into executable steps, execution nodes that follow plans systematically, verification nodes that check step success, replanning nodes that adjust failed plans, and conditional routing based on verification outcomes. You'll learn how to create state schemas with plan tracking fields, build planning prompts that generate structured execution plans, implement tool execution with result capture, design verification logic that evaluates step quality, and implement replanning mechanisms that adapt when verification fails.

## Problem Statement

Build a Plan-Act-Check-based market research agent that responds to research queries by creating a multi-step execution plan, executing research steps with real web searches, verifying each step's quality, and replanning if needed. You need to implement state schemas with plan and execution tracking fields, planning prompts that decompose queries into executable steps, graph nodes for planning, execution, verification, and replanning, conditional routing based on verification status, and FastAPI endpoints that process research queries and return structured results.

You will complete multiple implementation tasks to build this Plan-Act-Check agent:


## Task 1 — Implement Tools

### Goal

Build the tool functions that the agent will use to search the web and perform calculations.

### Requirements

1. Import required modules
2. Initialize DuckDuckGoSearchRun
3. Implement `search_web` tool function
4. Implement `calculate` tool function

**File:** `tools/tools.py`

## Task 2 — Implement Planning Node

### Goal

Build a planning node that decomposes user research queries into structured, executable multi-step plans.

### Requirements

1. Import required modules
2. Implement `planning_node` that extracts user request, builds planning prompt, invokes LLM, parses JSON response, normalizes plan format, and updates state

**File:** `nodes/planner.py`

## Task 3 — Implement Execution Node

### Goal

Build an execution node that executes individual steps from the plan using tools.

### Requirements

1. Import required modules
2. Implement `execution_node` that gets current step, invokes llm_with_tools, executes tools, and stores results

**File:** `nodes/executor.py`

## Task 4 — Implement Verification Node

### Goal

Build a verification node that checks if executed steps met success criteria.

### Requirements

1. Import required modules
2. Implement `verification_node` that evaluates step results, parses verification response, handles PASS/FAIL status, and updates state

**File:** `nodes/verifier.py`

## Task 5 — Implement Replanning Node

### Goal

Build a replanning node that adjusts plans when steps fail verification.

### Requirements

1. Import required modules
2. Define `MAX_REPLANS = 2` constant
3. Implement `replanning_node` that checks replan attempts, builds replanning prompt, invokes LLM, parses revised plan, and updates state

**File:** `nodes/replanner.py`

## Task 6 — Build Plan-Act-Check Graph

### Goal

Set up the routing logic and construct the complete LangGraph workflow with conditional routing.

### Requirements

1. Import required modules
2. Define `MAX_STEPS = 10` constant
3. Implement `should_continue` routing function
4. Build StateGraph with nodes, edges, and conditional routing

**File:** `graph/graph.py`

## Task 7 — Implement FastAPI Endpoint

### Goal

Build REST API endpoint that processes research queries and returns structured results.

### Requirements

1. Import required modules
2. Create FastAPI app
3. Implement `POST /research` endpoint


**File:** `main.py`

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. **Tool Implementation**: search_web function is decorated with @tool, accepts query parameter, initializes DuckDuckGoSearchRun with timeout, invokes ddg_search.invoke(query), handles empty results, handles exceptions, and returns search result string. calculate function is decorated with @tool, accepts expression parameter, uses try-except block, evaluates expression safely using eval with restricted builtins, formats result with rounding, handles exceptions, and returns formatted result string.

2. **Planning Node Implementation**: planning_node function has correct signature accepting state parameter. Function extracts user_request from state messages, builds planning prompt with tool inventory and JSON format specification, invokes llm.invoke() with SystemMessage and HumanMessage, parses JSON from response.content (handles markdown fences), normalizes plan format (handles dict and string items), limits plan to 5 steps, updates state with plan and initialization values, and returns updated state. Function handles JSONDecodeError with fallback plan.

3. **Execution Node Implementation**: execution_node function has correct signature accepting state parameter. Function performs safety checks, gets current step information from plan, creates execution message, invokes llm_with_tools.invoke() with messages, appends response to messages, handles no tool call case, executes tool (search_web or calculate), stores execution result in execution_results, adds ToolMessage to messages, and returns updated state. Function handles all edge cases correctly.

4. **Verification Node Implementation**: verification_node function has correct signature accepting state parameter. Function performs safety checks, gets step info and execution result, builds verification prompt with expected vs actual comparison, invokes llm.invoke() for evaluation, parses JSON verification result (handles markdown fences), stores verification status, handles FAIL status (sets needs_replanning), handles PASS status (advances step or marks complete), and returns updated state. Function handles JSONDecodeError with default PASS status.

5. **Replanning Node Implementation**: replanning_node function has correct signature accepting state parameter. Function increments replan_attempts, checks max replan attempts (fail-forward logic), gets failure context, builds replanning prompt with full context (original plan, failed step, failure reason, execution result), invokes llm.invoke() for replanning, parses revised plan JSON, normalizes revised plan format, updates state with revised plan, handles JSONDecodeError with step simplification, and returns updated state. Function limits replan attempts to MAX_REPLANS.

6. **Routing Function Implementation**: should_continue function has correct signature accepting state parameter and returns str. Function checks task_complete flag, checks max steps safety limit, checks needs_replanning flag, and returns appropriate string ("complete", "replan", or "execute"). Function handles all edge cases correctly.

7. **Graph Construction Implementation**: StateGraph is created with MarketResearchState schema. All nodes are registered (planner, executor, verifier, replanner). Entry point is set to "planner". Edges are added correctly (planner->executor, executor->verifier, replanner->executor). Conditional edges are added from "verifier" with should_continue function and proper mapping (execute->executor, replan->replanner, complete->END). Graph is compiled correctly and stored in app_graph variable.

8. **FastAPI Endpoint Implementation**: POST /research endpoint is decorated with @app.post("/research") and accepts query parameter. Endpoint validates query input, initializes state correctly with all required fields, invokes graph with timeout using asyncio.wait_for and asyncio.to_thread, handles TimeoutError, handles general Exception, and returns success response with status, task_complete, plan, execution_results, and verification_status. GET /health endpoint returns {"status": "healthy"}. Server runs correctly with uvicorn.

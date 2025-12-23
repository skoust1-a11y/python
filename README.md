# Banking Customer Support ReAct Agent - Sprint Practice

## Project Context

You're building a Banking Customer Support ReAct Agent, an AI-powered system that helps bank customers with account queries by reactively using tools step by step. The system uses a ReAct (Reasoning + Acting) pattern to reason about customer queries, decide which tools to use, execute them, observe results, and provide clear answers.

This practice focuses on building ReAct agents with LangGraph — implementing reasoning-action-observation loops, tool integration, and conditional routing based on tool calls vs final answers. You'll learn how to create state schemas with ReAct tracking fields, build reasoning nodes that generate explicit decision traces, implement tool execution nodes, design prompts that elicit structured reasoning, and implement loop control with completion criteria.

## Problem Statement

Build a ReAct-based customer support agent for a bank that answers user queries by looking up account information, performing calculations when needed, and producing clear answers based on tool observations. You need to implement state schemas with ReAct tracking fields, reasoning prompts, graph nodes for reasoning and tool execution, conditional routing based on tool calls vs final answers, and FastAPI endpoints that process customer queries.

You will complete multiple implementation tasks to build this ReAct agent:

## Task 1 — Define State Schema

### Goal

Build the foundational data structure for ReAct state management with tracking fields for thoughts, actions, and observations.

### Requirements

1. Import `TypedDict`, `List`, `Dict`, `Annotated` from `typing` and `operator` module
2. Define `CustomerSupportState` TypedDict with:
   - `messages: Annotated[List, operator.add]` - Conversation history
   - `thought_history: Annotated[List[str], operator.add]` - Agent's reasoning traces
   - `action_log: Annotated[List[Dict], operator.add]` - Tools called and their inputs
   - `observation_results: Annotated[List[str], operator.add]` - Tool outputs
   - `task_complete: bool` - Termination flag

**File:** `state.py`

## Task 2 — Create Reasoning Prompt

### Goal

Design a system prompt that guides the agent through ReAct-style reasoning and tool usage.

### Requirements

1. Create `REASONING_PROMPT` string template with:
   - Role definition as bank customer support assistant
   - Context placeholders: `{thought_history}`, `{action_log}`, `{observation_results}`
   - Available tools section: `get_account_info` and `calculate` with usage instructions
   - ReAct-style loop instructions: THINK → DECIDE → Use tool → OBSERVE → Continue
   - Thinking guidelines and output format (THOUGHT, FINAL ANSWER)
   - Important notes about tool calling and step-by-step reasoning

**File:** `prompts.py`

## Task 3 — Implement Tools

### Goal

Build the tool functions that the agent will use to gather information and perform calculations.

### Requirements

1. Import `tool` decorator from `langchain_core.tools`
2. Keep the `ACCOUNT_DB` dictionary (already provided)
3. Implement `get_account_info(account_id: str) -> str`:
   - Get account from `ACCOUNT_DB` using `account_id.upper()` as key
   - Return formatted string with account type, balance (formatted with commas), and interest rate
   - Return error message if account not found
4. Implement `calculate(expression: str) -> str`:
   - Use try-except block to safely evaluate the expression using `eval()`
   - Return formatted result or error message

**File:** `tools.py`

## Task 4 — Initialize LLM with Tools

### Goal

Set up the Azure OpenAI LLM instance with tools bound to it.

### Requirements

1. Initialize `AzureChatOpenAI` with credentials from environment variables
2. Set `temperature=0` and default model to "gpt-4o-mini"
3. Bind tools `[get_account_info, calculate]` to the LLM using `.bind_tools()`

**File:** `main.py` (in the initialization section)

## Task 5 — Implement Reasoning Node

### Goal

Build the reasoning node that analyzes queries and decides next action or provides final answer.

### Requirements

1. Implement `reasoning_node(state: CustomerSupportState)` function that:
   - Formats `REASONING_PROMPT` with state fields (thought_history, action_log, observation_results)
   - Prepends `SystemMessage` with formatted prompt to messages
   - Invokes LLM with messages
   - Extracts thought from response if present, appends to `state["thought_history"]`, and logs it
   - Sets `state["task_complete"] = True` if "FINAL ANSWER" in response content
   - Returns `{"messages": [response]}`

**File:** `main.py`

## Task 6 — Implement Tool Execution Node

### Goal

Build the tool execution node that executes selected tools and returns observations.

### Requirements

1. Implement `tool_execution_node(state: CustomerSupportState)` function that:
   - Gets last message from state and checks for `tool_calls`
   - Loops through all `tool_calls`:
     - Extracts tool name and args, creates action dict, appends to `state["action_log"]`, and logs action
     - Executes appropriate tool (get_account_info or calculate)
     - Appends result to `state["observation_results"]` and logs observation
     - Creates `ToolMessage` with result and `tool_call_id`
   - Returns `{"messages": tool_messages}`

**File:** `main.py`

## Task 7 — Implement Loop Condition

### Goal

Build the conditional routing function that determines if the agent should continue or finish.

### Requirements

1. Implement `should_continue(state: CustomerSupportState) -> str` function that:
   - Returns "end" if `task_complete` is True or "FINAL ANSWER" in last message content
   - Returns "continue" if last message has `tool_calls` (check max 6 iterations)
   - Returns "continue" if last message is a `ToolMessage`
   - Returns "end" as default fallback

**File:** `main.py`

## Task 8 — Build the Graph

### Goal

Construct the LangGraph workflow with reasoning and tool execution nodes.

### Requirements

1. Create `StateGraph` with `CustomerSupportState`
2. Add nodes: "reasoning" and "tool_execution"
3. Set entry point to "reasoning"
4. Add conditional edges from "reasoning" using `should_continue` function:
   - "continue" -> "tool_execution"
   - "end" -> END
5. Add edge from "tool_execution" back to "reasoning"
6. Compile the graph

**File:** `main.py`

## Task 9 — Implement FastAPI Endpoint

### Goal

Build REST API endpoint that processes customer queries and returns final answers.

### Requirements

1. Build graph using the graph construction code (from Task 8)
2. Implement `POST /support/query` endpoint that:
   - Accepts `query: str` parameter
   - Initializes state with messages, thought_history, action_log, observation_results, task_complete
   - Invokes `react_graph` with the state
   - Extracts final answer from result messages (find "FINAL ANSWER" and clean up formatting)
   - Logs query and final answer
   - Returns `{"answer": final_answer}`

**File:** `main.py`

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. **State Schema Definition**: CustomerSupportState TypedDict is defined with messages (Annotated[List, operator.add]), thought_history (Annotated[List[str], operator.add]), action_log (Annotated[List[Dict], operator.add]), observation_results (Annotated[List[str], operator.add]), and task_complete (bool) fields. All imports (TypedDict, List, Dict, Annotated, operator) are correctly included.

2. **Reasoning Prompt Implementation**: REASONING_PROMPT string template includes role definition, context placeholders ({thought_history}, {action_log}, {observation_results}), available tools section, ReAct-style loop instructions, thinking guidelines, output format, and important notes. Prompt uses .format() method placeholders correctly.

3. **Tool Implementation**: get_account_info function is decorated with @tool, accepts account_id parameter, retrieves account from ACCOUNT_DB using account_id.upper(), handles not found case, and returns formatted string with account type, balance (formatted with commas), and interest rate. calculate function is decorated with @tool, accepts expression parameter, uses try-except block, evaluates expression safely, returns formatted result, and handles exceptions.

4. **LLM Initialization**: AzureChatOpenAI is initialized with all required parameters from environment variables (api_key, azure_endpoint, model with default, api_version, temperature=0). Tools [get_account_info, calculate] are bound to LLM using .bind_tools().

5. **Reasoning Node Implementation**: reasoning_node function has correct signature accepting state parameter. Function formats REASONING_PROMPT with state fields, gets messages from state, prepends SystemMessage with prompt, invokes LLM, extracts thought if present, appends to thought_history, logs thought, checks for FINAL ANSWER and sets task_complete, and returns {"messages": [response]}. Function does not return None or empty dict.

6. **Tool Execution Node Implementation**: tool_execution_node function has correct signature accepting state parameter. Function gets last message, checks for tool_calls, loops through all tool_calls, extracts tool_name and tool_args, creates action dict, appends to action_log, logs action, executes appropriate tool, appends result to observation_results, logs observation, creates ToolMessage with correct tool_call_id, and returns {"messages": tool_messages}. Function handles all tool_calls, not just the first one.

7. **Loop Condition Implementation**: should_continue function has correct signature accepting state parameter and returns str. Function checks task_complete flag, checks for FINAL ANSWER in content, checks for tool_calls and max iterations, checks for ToolMessage, and returns appropriate string ("continue" or "end"). Function handles all edge cases correctly.

8. **Graph Construction Implementation**: StateGraph is created with CustomerSupportState schema. All nodes are registered (reasoning, tool_execution). Entry point is set to "reasoning". Conditional edges are added from "reasoning" with should_continue function and proper mapping. Edge is added from "tool_execution" back to "reasoning". Graph is compiled correctly. Function does not return None.

9. **FastAPI Endpoint Implementation**: POST /support/query endpoint is decorated with @app.post("/support/query") and accepts query parameter. Endpoint initializes state correctly with all required fields, invokes react_graph, extracts final answer correctly (handles FINAL ANSWER extraction and cleanup), logs query and final answer, and returns {"answer": final_answer}. Endpoint handles edge cases (no FINAL ANSWER found).

10. **Main Block Implementation**: Main block includes uvicorn.run() to start the server with appropriate host, port, and reload settings.

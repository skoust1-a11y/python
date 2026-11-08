# Quick Commerce Support Agent

## Project Context

You're building a Quick Commerce Support Agent, an AI-powered system that helps customers with order issues, refunds, and general inquiries through multi-turn conversations.

This practice focuses on building stateful agents with LangGraph — implementing state management, graph nodes, and checkpointing to maintain conversation context across multiple interactions. You'll learn how to create state schemas with reducers, build graph nodes that process conversation state, and implement REST APIs that persist conversation history using thread-based checkpointing.

## Problem Statement

Build a multi-turn conversational support agent using LangGraph with checkpointing capabilities. The system must support stateful conversations, extract user information, identify issue types, and maintain conversation context across multiple API calls. You need to implement state schemas, graph nodes for conversation flow, and FastAPI endpoints that handle thread-based state persistence.

You will complete multiple implementation tasks to build this support agent:

## Task 1 — Define State and API Schemas

### Goal

Build the foundational data structures for state management and API request/response models.

### Requirements

1. Implement `SupportAgentState` TypedDict with messages, user_name, issue_type, conversation_stage
2. Implement `MessageRequest` Pydantic model with message and thread_id
3. Implement `MessageResponse` Pydantic model with messages, user_name, issue_type, conversation_stage, thread_id
4. Implement `ConversationStateResponse` Pydantic model with thread_id, user_name, issue_type, conversation_stage, message_count

**File:** `schemas.py`

## Task 2 — Implement Graph Nodes and Builder

### Goal

Build graph nodes that handle conversation flow and create the compiled graph with checkpointing.

### Requirements

1. Implement `greeting_node()` to send greeting if user_name missing
2. Implement `identify_issue_node()` to extract name and ask for issue
3. Implement `resolve_node()` to identify issue type and acknowledge
4. Implement `build_graph()` to create graph with nodes, edges, entry/finish points, and checkpointing

**File:** `graph.py`

## Task 3 — Implement FastAPI Endpoints

### Goal

Build REST API endpoints that process chat messages and retrieve conversation state with checkpointing support.

### Requirements

1. Implement `get_graph()` singleton function
2. Implement `POST /chat` endpoint to process messages with checkpointing
3. Implement `GET /conversation/{thread_id}` endpoint to retrieve conversation state

**File:** `main.py`

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. **State Schema Definition**: SupportAgentState TypedDict is defined with messages (Annotated[list, add_messages]), user_name, issue_type, and conversation_stage fields. All Pydantic models (MessageRequest, MessageResponse, ConversationStateResponse) are properly defined with correct field types and optional/required annotations. All models can be instantiated and serialized to JSON.

2. **greeting_node Implementation**: greeting_node function has correct signature (state: SupportAgentState) -> dict. Function checks if user_name exists in state and returns empty dict {} when it does. Returns dict with messages containing AIMessage("Hi! What's your name?") and conversation_stage: "greeting" when user_name is missing. Function does not return None.

3. **identify_issue_node Implementation**: identify_issue_node function has correct signature (state: SupportAgentState) -> dict. Function accesses state messages and extracts name from last HumanMessage when user_name is missing. Returns dict with user_name, AIMessage with thanks message, and conversation_stage: "identifying" when name is extracted. Returns empty dict {} when conditions are not met. Function does not return None.

4. **resolve_node Implementation**: resolve_node function has correct signature (state: SupportAgentState) -> dict. Function checks if issue_type is missing and accesses last HumanMessage from state. Identifies issue type correctly: "order" if "order" in content (case-insensitive), "refund" if "refund" in content (case-insensitive), else "other". Returns dict with issue_type, AIMessage with acknowledgment, and conversation_stage: "resolved". Returns empty dict {} when issue_type already exists. Function does not return None.

5. **build_graph Implementation**: build_graph function has correct signature (checkpointer=None). Creates StateGraph with SupportAgentState schema. Adds all three nodes: "greeting", "identify_issue", "resolve". Connects nodes with edges: greeting -> identify_issue -> resolve. Sets entry point to "greeting" and finish point to "resolve". Uses MemorySaver() if checkpointer is None. Compiles graph with checkpointer and returns compiled graph. Function does not return None.

6. **get_graph Singleton Implementation**: get_graph() function implements singleton pattern correctly by checking _graph global variable and caching build_graph() result. Function returns the same graph instance on subsequent calls. Function does not return None.

7. **POST /chat Endpoint Implementation**: POST /chat endpoint is decorated with @app.post("/chat", response_model=MessageResponse) and accepts MessageRequest parameter. Endpoint handles thread_id generation using uuid.uuid4() if not provided in request. Creates config dict with thread_id: {"configurable": {"thread_id": thread_id}}. Gets current state from graph using graph.get_state(config). Handles first message (initializes state) vs subsequent messages (invokes with HumanMessage). Converts messages to dict format with "type" and "content" keys. Returns MessageResponse with all state fields (messages, user_name, issue_type, conversation_stage, thread_id). Endpoint handles exceptions gracefully with HTTPException.

8. **GET /conversation/{thread_id} Endpoint Implementation**: GET /conversation/{thread_id} endpoint is decorated with @app.get("/conversation/{thread_id}", response_model=ConversationStateResponse) and accepts thread_id path parameter. Endpoint creates config dict with thread_id: {"configurable": {"thread_id": thread_id}}. Retrieves state from checkpoint using graph.get_state(config). Raises HTTPException(status_code=404) when state.values is None (conversation not found). Returns ConversationStateResponse with all state fields (thread_id, user_name, issue_type, conversation_stage, message_count). Endpoint handles exceptions gracefully.





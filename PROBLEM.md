
# Sprint 9 Practice Assignment: Observability for Your Trip and Travel Planner Agent (Langfuse + OpenTelemetry)

## Project Context

In this sprint you learned how to add end-to-end observability to LLM applications.  
You instrumented a FastAPI + LangChain backend to emit spans and traces and explored two approaches:

- Using a lightweight `@observe` decorator (Langfuse) combined with **OpenTelemetry** spans (console/OTLP).
- Using the **Langfuse Callback Handler** to automatically trace LangChain executions, tokens, and costs with session/user correlation.

By the end, your app will be fully observable: you’ll see traces, spans, token usage, and be able to correlate requests by session and user.

---

## Problem Statement

Your task is to implement observability in two ways on your existing FastAPI + LangChain app:
1) via the `@observe` decorator with OpenTelemetry spans, and  
2) via the Langfuse Callback Handler with session/user metadata and flushing.

---

### Task 1 — Add Observability with `@observe` Decorator (Security only)

#### Goal  
Apply the `@observe` decorator strictly in the security layer so you can observe authentication/authorization behavior. Optionally initialize OpenTelemetry so spans print to console.

#### Requirements  
1. Add the `@observe` decorator only to security functions, for example:
   - ` _fetch_jwks(...)`
   - `get_user_email_from_auth0(...)`
2. Do not decorate FastAPI endpoints or business logic in this task.
3. Initialize OpenTelemetry with a Console exporter so spans are visible in logs.
4. Add a shutdown hook to flush traces if you enabled a tracer/exporter.
5. Set Langfuse environment variables to send traces to Langfuse.

Environment variables (example):
```
GEMINI_API_KEY=...
GEMINI_BASE_URL=...
GEMINI_MODEL_NAME=...
# Optional (to send to Langfuse cloud or self-hosted):
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
```

**Expected Output:**  
- Console (and/or Langfuse) shows traces/spans originating from security flows (e.g., token validation, userinfo lookup).  
- No endpoint/business-logic functions are decorated in this task.

---

### Task 2 — Add Observability with Langfuse Callback Handler (Chat API)

#### Goal  
Attach the Langfuse Callback Handler in your chat API so all chain events (LLM calls, tokens, costs) and metadata (session/user) are captured automatically.

#### Requirements  
1. Implement a `LangfuseCallbackManager` (or equivalent) that can return a configured `CallbackHandler`.
2. Create a helper (e.g., `setup_langfuse_callback(session_id, token_payload)`) that:
   - Resolves the user identity from the JWT payload (email if present; else fetch from userinfo; else fall back to `sub`).
   - Creates a callback handler instance and builds a chain `config` with:
     - `callbacks: [handler]`
     - `metadata` including `session_id`, `user_id`/`user_email`, `trace_name` (e.g., `route_query`), and relevant tags.
3. Update your chat endpoint (e.g., `POST /chat` ) to execute the chain with the `config` above and stream responses.
4. Ensure traces are flushed (e.g., in a `finally` block) to avoid losing the tail of a streamed response.
5. Add Langfuse environment variables:
```
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
```

**Expected Output:**  
- Langfuse dashboard shows traces for each request with:
  - All chain steps and LLM calls
  - Token usage and costs
  - Metadata (session_id, user) enabling correlation across requests
  - A recognizable trace name (e.g., `chat`)

---

##  Expected Outcome

| Concept | Demonstrated Through |
|----------|----------------------|
| OpenTelemetry span creation and flushing | Task 1 |
| Langfuse `@observe` decorator traces | Task 1 |
| Langfuse Callback Handler with metadata | Task 2 |
| Session and user correlation in traces | Task 2 |
| Token usage and cost tracking | Task 2 |

---

##  By the End of This Sprint

You’ll have an **observable, full-stack LLM application** where:  
- Key backend operations emit OpenTelemetry spans (and optionally Langfuse traces).  
- Chain executions are traced end-to-end with session/user correlation.  
- You can analyze latency, tokens, costs, and behavior in your logs or the Langfuse dashboard.
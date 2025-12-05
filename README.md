## Project Context

In earlier practice, you built a full-stack LLM application with FastAPI and LangChain.  
However, without observability, it's difficult to understand how your application behaves in production — you can't see traces, token usage, costs, or correlate requests by session and user.

In this practice, you will add end-to-end observability to your LLM application using two approaches:
- Using a lightweight `@observe` decorator (Langfuse) combined with **OpenTelemetry** spans
- Using the **Langfuse Callback Handler** to automatically trace LangChain executions, tokens, and costs with session/user correlation

By the end, your app will be fully observable: you'll see traces, spans, token usage, and be able to correlate requests by session and user.

---

## Problem Statement

Implement observability in your existing FastAPI + LangChain application using two complementary approaches: the `@observe` decorator with OpenTelemetry spans for security operations, and the Langfuse Callback Handler for comprehensive chain tracing with session/user metadata.  
You will complete **two main tasks**:

---

### **Task 1 — Add Observability with `@observe` Decorator**

#### Goal  
Apply the `@observe` decorator to security functions to observe authentication and authorization behavior, and optionally initialize OpenTelemetry so spans are visible in logs.

#### Requirements  
1. Add the `@observe` decorator to functions such as token validation and user info lookup (e.g., authentication and authorization logic).

2. Initialize OpenTelemetry with a Console exporter so spans are visible in logs.

3. Add a shutdown hook to flush traces if you enabled a tracer/exporter.

4. Configure Langfuse environment variables to send traces to Langfuse (if using cloud or self-hosted instance).

---

### **Task 2 — Add Observability with Langfuse Callback Handler**

#### Goal  
Attach the Langfuse Callback Handler in your chat API so all chain events (LLM calls, tokens, costs) and metadata (session/user) are captured automatically.

#### Requirements  
1. Implement a callback manager that can return a configured Langfuse callback handler.

2. Create a helper function that:
   - Resolves the user identity from the JWT payload (e.g., email, user ID).
   - Creates a callback handler instance and builds a chain configuration with:
     - Callbacks including the handler
     - Metadata including `session_id`, `user_id`/`user_email`, `trace_name`, and relevant tags.

3. Update your chat endpoint to execute the chain with the configured callbacks and stream responses.

4. Ensure traces are flushed (e.g., in a `finally` block) to avoid losing the tail of a streamed response.

5. Configure Langfuse environment variables for the callback handler.

---

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. `@observe` decorator is correctly applied.
2. OpenTelemetry spans are properly initialized and visible in console logs.
3. Langfuse Callback Handler is properly configured and attached to chain executions.
4. Traces include proper metadata (session_id, user_email, trace_name) enabling correlation across requests.
5. Traces are correctly flushed to avoid losing data from streamed responses.


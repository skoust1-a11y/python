# 🧳 Sprint 6 Practice Assignment: Adding Memory to the Travel & Trip Planner Agent

## Project Context

In Sprint 5, your **Travel & Trip Planner Agent** became intelligent — it could classify and route queries such as **booking**, **cancellation**, or **general inquiries** using LCEL pipelines.  
However, the agent still suffered from **amnesia** — it forgot everything after each response.

In this sprint, you will enable **short-term memory** for your agent so it can hold meaningful **multi-turn conversations**.  
Your upgraded agent will now **remember user details** like destination, duration, and preferences across messages in the same session.

---

## Learning Goals

By completing this sprint, you will learn how to:
  
1. Use **MessagesPlaceholder** to make prompts memory-aware.  
2. Implement **RunnableWithMessageHistory** for automatic memory management per session.  
3. Build a **stateful FastAPI chat endpoint** that can remember context.

---

## Problem Statement

You will extend your **Travel & Trip Planner Agent** into a **stateful conversational agent** that remembers trip details across multiple turns using **LangChain Expression Language (LCEL)** components.

Your agent should maintain context *within the same session* but start fresh for new sessions.

---

## Task 1 — Create a Memory-Aware Prompt

### Goal  
Build a prompt that can **accept and display conversation history** using `MessagesPlaceholder`.

### Requirements

1. Create a file named `trip_memory_prompt.py`.  
2. Initialize the LLM using your Gemini API key with `ChatOpenAI`.  
3. Build a `ChatPromptTemplate` that includes:  
   ```python
   ("system", "You are a helpful travel assistant. You remember the user's travel plans during the conversation."),
   MessagesPlaceholder(variable_name="chat_history"),
   ("user", "{input}")
   ```
4. Create a small script to test the prompt with a manually created `chat_history` list of messages.  
5. Print the formatted output to verify that the history is inserted correctly.

### Expected Output Example
```
System: You are a helpful travel assistant.
Human: I want to visit Bali.
AI: Great! How many days are you planning to stay?
Human: Add snorkeling and a sunset cruise.
```

---

## Task 2 — Build a Stateful Trip Planner API

### Goal  
Create a **FastAPI-based AI agent** that remembers trip details across turns within the same session using `RunnableWithMessageHistory`.

### Requirements

1. Create a file named `stateful_trip_agent.py`.  
2. Import the necessary modules:
3. Initialize the LLM using your Gemini API key.  
4. Define a `get_session_history(session_id: str)` function that returns a unique `InMemoryChatMessageHistory` per session.  
5. Create a `ChatPromptTemplate` that includes a `MessagesPlaceholder(variable_name="chat_history")`.  
6. Create a core LCEL chain:
   ```python
   core_chain = prompt | llm
   ```
7. Wrap it using:
   ```python
   stateful_chain = RunnableWithMessageHistory(
       runnable=core_chain,
       get_session_history=get_session_history,
       input_messages_key="input",
       history_messages_key="chat_history"
   )
   ```
8. Add a FastAPI endpoint `/chat`:
   - Accepts query params: `input` (user message) and `session_id`.  
   - Invokes the `stateful_chain` using:
     ```python
     response = stateful_chain.invoke(
         {"input": input},
         config={"configurable": {"session_id": session_id}}
     )
     ```
   - Returns a JSON response with `session_id`, `user_input`, and `response`.

---

### Expected Behavior

| Step | User Input | Expected Response |
|------|-------------|------------------------|
| 1 | “Book me a 3-day trip to Bali.” | “Sure! A 3-day Bali itinerary — do you have preferred travel dates?” |
| 2 | “Add snorkeling and a sunset cruise.” | “Got it — I’ll include snorkeling and a sunset cruise in your Bali plan.” |
| 3 | “What activities did I add?” | “You’ve added snorkeling and a sunset cruise to your Bali trip.” |
| 4 | (new session) “Do you remember my trip?” | “I don’t have any trip details yet. Let’s start planning!” |

---

## Project Setup

### Environment Setup
Create a `.env` file:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL_NAME=gemini-2.0-flash
```

### Install Dependencies
```bash
uv sync
```
### Run the trip_memory_prompt
```bash
uv run uvicorn trip_memory_prompt:app --host 0.0.0.0 --port 8000 --reload
```
### Run the stateful_trip_agent
```bash
uv run uvicorn stateful_trip_agent:app --host 0.0.0.0 --port 8000 --reload
```

### Test in Swagger UI
Open: [http://localhost:8000/docs](http://localhost:8000/docs)



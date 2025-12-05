## Project Context

In earlier practice, your **Travel & Trip Planner Agent** became intelligent — it could classify and route queries such as **booking**, **cancellation**, or **general inquiries** using LCEL pipelines.  
However, the agent still suffered from amnesia — it forgot everything after each response.

In this practice, you will enable **short-term memory** for your agent so it can hold meaningful **multi-turn conversations**. Your upgraded agent will now **remember user details** like destination, duration, and preferences across messages in the same session.

---

## Problem Statement

Extend your **Travel & Trip Planner Agent** into a **stateful conversational agent** that remembers trip details across multiple turns using **LangChain Expression Language (LCEL)** components.  
Your agent should maintain context within the same session but start fresh for new sessions.  
You will complete **two main tasks**:

---

### **Task 1 — Create a Memory-Aware Prompt**

#### Goal  
Build a prompt that can accept and display conversation history using `MessagesPlaceholder` to make the agent memory-aware.

#### Requirements  
1. Create a `ChatPromptTemplate` that includes a system message, a `MessagesPlaceholder` for chat history, and a user input placeholder.

2. Test the prompt with manually created chat history to verify that conversation history is correctly inserted into the prompt.

3. Ensure the prompt structure allows the LLM to access and reference previous conversation turns when generating responses.

---

### **Task 2 — Build a Stateful Trip Planner API**

#### Goal  
Create a FastAPI-based AI agent that remembers trip details across turns within the same session using `RunnableWithMessageHistory`.

#### Requirements  
1. Implement a session management function that returns a unique chat message history for each session ID, initializing it if it doesn't already exist.

2. Create a `ChatPromptTemplate` that includes a `MessagesPlaceholder` for chat history to enable memory-aware conversations.

3. Build a core LCEL chain that combines the prompt with the LLM.

4. Wrap the core chain using `RunnableWithMessageHistory` to enable automatic memory management per session, configuring the input and history message keys appropriately.

5. Create a FastAPI endpoint `/new-session` that generates and returns a unique session ID for each new chat.

6. Create a FastAPI endpoint `/chat` that accepts user input and session ID, invokes the stateful chain with the appropriate configuration, and returns the session ID, user input, and agent's response.

---

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. Memory-aware prompt correctly includes `MessagesPlaceholder` and formats conversation history appropriately.
2. Session management function correctly creates and retrieves unique chat message histories for different session IDs.
3. Stateful chain is properly configured with `RunnableWithMessageHistory` and maintains conversation context within sessions.
4. Agent remembers user details (e.g., destination, duration, preferences) across multiple turns within the same session.



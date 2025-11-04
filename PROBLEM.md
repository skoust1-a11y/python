# Sprint 7 Practice Assignment: Building Frontends for the Trip & Travel Planner Agent

## Project Context

In **Sprint 6**, your **Travel & Trip Planner Agent** became stateful — it could remember destinations, activities, and preferences across sessions using `RunnableWithMessageHistory`.  
Now, it’s time to give that intelligent backend a **face**. In this sprint, you’ll learn to build user-friendly **frontend** so travelers can actually chat with your agent instead of using terminal commands.  

Create and connect a **React UI** to your FastAPI backend for a full-stack experience.  

---

## Problem Statement

Design and implement interactive frontend that connect to your existing **stateful travel agent backend** built in Sprint 6.  
You will complete **one major tasks**:  

### **Task 1 — Connect a React Frontend to the FastAPI Agent**

#### Goal  
Build a React chat UI that communicates with your FastAPI `/chat` endpoint, sending both the user’s message and the `session_id` to maintain conversation memory.

#### Requirements  
1. **Backend**  
   - Ensure your FastAPI server exposes a `/chat` POST endpoint that accepts:  
     ```json
     { "input": "user message", "session_id": "uuid" }
     ```  
   - The endpoint should stream responses using Server-Sent Events (SSE) format for real-time token-by-token updates.
   - Add CORS middleware to allow requests from `http://localhost:5173` (Vite default port) and `http://localhost:3000`.  
2. **Frontend**  
   - Use the provided React boilerplate with Vite.  
   - In `apiService.ts`: define `streamChatMessage(input, sessionId, onMessage)` using `fetch()` with ReadableStream to handle streaming responses from your FastAPI endpoint.  
   - In `ChatComponent.tsx`:  
     - Use `useState()` for `messages`, `input`, `sessionId`, and `isLoading`.  
     - Generate `sessionId` once via `uuidv4()` in `useEffect()`.  
     - Append new messages to history, call `streamChatMessage` with a callback to update messages in real-time as tokens arrive, and display the assistant's reply.  
     - Implement markdown rendering for AI responses using ReactMarkdown.  
3. Start both servers:  
   ```bash
   # Backend
   cd backend
   uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   
   # Frontend (in a separate terminal)
   cd frontend/react-frontend
   npm install
   npm run dev
   ```  
4. Test a full conversation in your browser at `http://localhost:5173` (Vite default port).

**Expected Output:**  
A responsive React chat app with real-time streaming responses where each new session starts fresh, but within the session the agent remembers prior turns using the same `session_id`. Responses should appear token-by-token as they're generated, providing immediate feedback to users. AI responses should support markdown formatting (headings, lists, code blocks, links, etc.).

---

## Expected Outcome  

By the end of Sprint 7, your Trip & Travel Planner Agent will be accessible through an interactive frontend:  
| Concept | Demonstrated Through |
|----------|----------------------|
| Full-stack React integration with streaming | Task 1 |

---


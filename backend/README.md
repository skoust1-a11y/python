# Stateful Travel & Trip Planner Agent

A FastAPI application demonstrating how to build a **stateful travel assistant** using **LangChain Expression Language (LCEL)** and **ChatMessageHistory**.  
This backend service provides conversational travel planning capabilities that maintain context across multiple interactions within each session, with **real-time streaming responses** for enhanced user experience.

---

## Features

- **Stateful LCEL Chain:** Maintains conversation memory using `RunnableWithMessageHistory` for context-aware responses  
- **Session-Based Context:** Each conversation is tracked via a unique `session_id` for isolated memory management  
- **Travel Planning Assistance:** Specialized travel assistant that remembers trip details, activities, and preferences during sessions  
- **FastAPI Integration:** Exposes `/chat` and `/new-session` endpoints for travel planning interactions  
- **Real-Time Streaming:** Token-by-token streaming responses using Server-Sent Events (SSE) for immediate user feedback
- **CORS Enabled:** Configured for frontend integration with localhost:5173 (Vite) and localhost:3000

---

## Prerequisites

- Python 3.12 or higher  
- [UV](https://docs.astral.sh/uv/) package manager  
- A Gemini API key from [Google AI Studio](https://ai.google.dev/) or OpenAI API key

---

## Configuration

Create a `.env` file in the backend directory with your API configuration:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL_NAME=gemini-2.0-flash
```

**Important:** 
- Replace `your_gemini_api_key_here` with your actual Gemini API key
- Keep the file named exactly `.env`

---

## Running the Application

### Linux

```bash
cd backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Windows

**PowerShell:**
```powershell
cd backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Command Prompt:**
```cmd
cd backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Alternative:** If `uv run` doesn't work, activate the virtual environment first:
```powershell
.venv\Scripts\Activate.ps1  # PowerShell
# or
.venv\Scripts\activate.bat  # Command Prompt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will start at:  
[http://localhost:8000](http://localhost:8000)

---

## API Endpoints

### **GET /new-session**

Generate a new chat session ID for starting a new conversation.

#### Response:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### **POST /chat**

Send a message to the travel assistant with **real-time streaming**.  
The assistant remembers previous messages **within the same session** and uses memory to provide context-aware replies.  
Responses are streamed token-by-token for immediate user feedback.

#### Request Body:
| Parameter | Type | Description |
|-----------|------|-------------|
| **input** | string | User message or travel query |
| **session_id** | string | Unique session identifier |

#### Request Example:

```http
POST /chat
Content-Type: application/json

{
  "input": "Book me a 3-day trip to Bali",
  "session_id": "travel_session_456"
}
```

#### Response Format (Server-Sent Events):

The endpoint returns a **streaming response** using Server-Sent Events (SSE) format:

```
data: I'd

data:  be

data:  happy

data:  to help

...

data: [DONE]
```

Each token is sent as it's generated, providing real-time feedback to the client.

#### Example Streaming Response:

The response is streamed progressively. The complete response might be:

"I'd be happy to help you plan a 3-day trip to Bali! To create the perfect itinerary for you, I'll need some information. What are your interests - are you looking for adventure, relaxation, culture, or a mix? Also, what's your approximate budget range?"

But it will be received token-by-token as:

```
data: I'd
data:  be
data:  happy
...
```

---

### **Follow-up Message (Same Session)**

```http
POST /chat
Content-Type: application/json

{
  "input": "I prefer beaches and some local culture",
  "session_id": "travel_session_456"
}
```

**Streaming Response:**
The assistant remembers the context from the previous message (the 3-day Bali trip request) and continues the planning conversation, streaming the response token-by-token.

Example complete response:
```
Perfect! Based on your preferences for beaches and local culture, here's a great 3-day Bali itinerary for you: Day 1 - Arrive and explore Seminyak Beach with sunset dinner at Tanah Lot Temple. Day 2 - Visit Ubud Monkey Forest and rice terraces, then enjoy Kuta Beach. Day 3 - Explore Sanur Beach and local markets. Would you like me to add any specific activities or adjust the itinerary?
```

---

### **Session Isolation Example**

Each `session_id` has isolated memory:

**Session A:**
```http
POST /chat
{
  "input": "What's the weather like in Paris?",
  "session_id": "session_A"
}
```

**Session B (Fresh Start):**
```http
POST /chat
{
  "input": "Plan a hiking trip in Colorado",
  "session_id": "session_B"
}
```

Each session maintains completely separate conversation histories.

---

## Project Structure

```
backend/
├── main.py              # Main FastAPI application with stateful LCEL chain and streaming
├── pyproject.toml       # Project dependencies and configuration
├── .env                 # Environment variables (create with your API key)
├── .gitignore          # Git ignore patterns
├── .python-version     # Python version specification
└── README.md           # This file
```

---

## Dependencies

- **FastAPI**: Modern web framework for building APIs
- **LangChain**: Framework for building LLM applications with LCEL
- **LangChain OpenAI**: OpenAI integration for LangChain (used with Gemini via custom base URL)
- **Uvicorn**: ASGI server for running FastAPI
- **Python-dotenv**: Environment variable management
- **Pydantic**: Data validation using Python type annotations
- **StreamingResponse**: FastAPI's streaming response support for real-time token delivery

---

## How It Works

The application uses a **stateful conversational system with streaming**:

1. **LLM Setup**: Uses ChatOpenAI with Gemini API (configurable via .env) with `streaming=True` enabled
2. **Prompt Template**: Specialized travel assistant prompt with system instructions and conversation history placeholder
3. **Memory Store**: In-memory dictionary stores `ChatMessageHistory` objects per session
4. **LCEL Chain**: Combines prompt template with LLM and `StrOutputParser` using the `|` operator
5. **Stateful Wrapper**: `RunnableWithMessageHistory` automatically handles conversation context
6. **Session Management**: Each request includes a `session_id` that maps to a unique message history
7. **Streaming**: Uses `astream()` method to yield tokens asynchronously, wrapped in `StreamingResponse` with SSE format

### Streaming Implementation

The `/chat` endpoint uses:
- **Async Streaming**: `stateful_chain.astream()` for non-blocking token-by-token generation
- **Server-Sent Events**: Responses are formatted as `data: {chunk}\n\n` for SSE compatibility
- **Error Handling**: Graceful error handling with error messages in the stream

---

## Testing the API

### Interactive Testing

Visit [http://localhost:8000/docs](http://localhost:8000/docs)  
to open **FastAPI's Swagger UI** and test the `/chat` and `/new-session` endpoints interactively.

**Note:** Swagger UI may not display streaming responses properly. For full streaming experience, use the frontend application or a tool that supports SSE.

### Using curl

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Plan a 3-day trip to Tokyo",
    "session_id": "test_session"
  }' \
  --no-buffer
```

The `--no-buffer` flag ensures streaming output is displayed immediately.

---

## CORS Configuration

The application is configured to accept requests from both Vite (port 5173) and React (port 3000) for frontend integration. To modify allowed origins, update the `allow_origins` parameter in `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Update as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Troubleshooting

### Common Issues

1. **Streaming Not Working**: Ensure the frontend client supports Server-Sent Events (SSE) or uses the Fetch API with ReadableStream
2. **Missing API Key Error**: Ensure your `.env` file contains a valid `GEMINI_API_KEY`
3. **Import Errors**: Make sure all dependencies are installed with `uv sync`
4. **Session Memory**: Each session maintains isolated memory - use the same `session_id` for related conversations
5. **CORS Errors**: Verify that the frontend origin is included in `allow_origins` in the CORS middleware configuration

---

## Key Implementation Details

- **Streaming Enabled**: LLM initialized with `streaming=True` for token-by-token generation
- **Async Streaming**: Uses `astream()` method for non-blocking async streaming in FastAPI
- **SSE Format**: Responses formatted as Server-Sent Events (`data: {content}\n\n`) for browser compatibility
- **StrOutputParser**: Converts LLM message chunks to strings for streaming
- **Memory Integration**: Streaming works seamlessly with `RunnableWithMessageHistory` for stateful conversations

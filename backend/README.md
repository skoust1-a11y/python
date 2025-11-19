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
- **CORS Enabled:** Configured for frontend integration with localhost:5173 (Vite)
- **Observability & Monitoring:** Integrated Langfuse for LLM tracing, token usage tracking, and cost monitoring, plus OpenTelemetry for distributed tracing

---

## Prerequisites

- Python 3.12 or higher  
- [UV](https://docs.astral.sh/uv/) package manager  
- A Gemini API key from [Google AI Studio](https://ai.google.dev/) or OpenAI API key
- Auth0 account and API configuration (for authentication)

---

## Configuration

Create a `.env` file in the backend directory with your API configuration:

```bash
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL_NAME=gemini-2.0-flash

# Auth0 Configuration (for JWT authentication)
AUTH0_DOMAIN=your-auth0-domain.auth0.com
API_AUDIENCE=your-api-audience-identifier
ALGORITHMS=RS256

# Langfuse Configuration 
# you have created these key in Sprint 3
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key_here
LANGFUSE_SECRET_KEY=your_langfuse_secret_key_here
LANGFUSE_HOST=https://cloud.langfuse.com
# Alternative: LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

**Important:** 
- Replace `your_gemini_api_key_here` with your actual Gemini API key
- Replace Auth0 configuration values with your actual Auth0 settings
- Langfuse configuration is - the application will work without it, but observability features will be disabled
- Keep the file named exactly `.env`

---

## Installation

Before running the application, install all dependencies:

```bash
cd backend
uv sync
```

This will install all required packages including FastAPI, LangChain, Python-JOSE, and other dependencies.

---

## Running the Application

**Important:** Always use `uv run` to ensure the virtual environment and dependencies are properly loaded. Running Python directly may result in `ModuleNotFoundError`.

### Linux/macOS

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install dependencies (if not already done):
   ```bash
   uv sync
   ```

3. Run the application:
   ```bash
   uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Windows (PowerShell)

1. Navigate to the backend directory:
   ```powershell
   cd backend
   ```

2. Install dependencies (if not already done):
   ```powershell
   uv sync
   ```

3. Run the application:
   ```powershell
   uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Windows (Command Prompt)

1. Navigate to the backend directory:
   ```cmd
   cd backend
   ```

2. Install dependencies (if not already done):
   ```cmd
   uv sync
   ```

3. Run the application:
   ```cmd
   uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Alternative: Activate Virtual Environment Manually

If `uv run` doesn't work, you can activate the virtual environment first:

**Linux/macOS:**
```bash
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Windows PowerShell:**
```powershell
.venv\Scripts\Activate.ps1
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Windows Command Prompt:**
```cmd
.venv\Scripts\activate.bat
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will start at:  
[http://localhost:8000](http://localhost:8000)

**Note:** The `--reload` flag enables auto-reload on code changes. Remove it for production deployments.

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

**⚠️ Authentication Required:** This endpoint requires a valid JWT token in the Authorization header.

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
├── observability.py     # Observability setup (Langfuse @observe decorator and OpenTelemetry)
├── security/            # Security module for JWT validation
│   ├── __init__.py     # Module initialization
│   └── security.py     # Auth0 JWT validation logic
├── callbacks/           # Callback handlers for observability
│   ├── __init__.py     # Module initialization
│   └── langfuse_callback.py  # Langfuse callback handler implementation
├── .env                 # Environment variables (create with your API key, Auth0, and Langfuse config)
├── .gitignore          # Git ignore patterns
├── .python-version     # Python version specification
└── README.md           # This file
```

---

## Dependencies

- **FastAPI**: Modern web framework for building APIs
- **LangChain**: Framework for building LLM applications with LCEL
- **LangChain OpenAI**: OpenAI integration for LangChain (used with Gemini via custom base URL)
- **LangChain Community**: Additional LangChain integrations and utilities
- **Uvicorn**: ASGI server for running FastAPI
- **Python-dotenv**: Environment variable management
- **Python-JOSE**: JWT token validation and JWKS handling
- **Requests**: HTTP client for JWKS fetching
- **Typing Extensions**: Extended type hints support
- **Langfuse**: LLM observability and tracing platform (optional)
- **OpenTelemetry**: Distributed tracing framework for observability

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

## Observability

This application includes observability features for monitoring LLM interactions:

### Langfuse Integration

**Langfuse** is integrated for LLM observability:
- Automatic tracing of all LLM calls with full context
- Token usage and cost tracking per request
- User tracking via Auth0 email
- Session grouping by `session_id`
- Traces are automatically flushed at the end of each request and on shutdown

**Configuration**: Add `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` to your `.env` file. Langfuse is optional - the application works without it.

### OpenTelemetry Integration

**OpenTelemetry** is configured for distributed tracing with console exporter. The setup is initialized automatically when the `observability` module is imported.

---

## Testing the API

### Interactive Testing

Visit [http://localhost:8000/docs](http://localhost:8000/docs)  
to open **FastAPI's Swagger UI** and test the `/chat` and `/new-session` endpoints interactively.

**Note:** 
- The `/chat` endpoint requires authentication. You'll need to:
  1. Get a valid JWT token from Auth0
  2. Click "Authorize" in Swagger UI
  3. Enter `Bearer <your_jwt_token>` in the authorization field
- Swagger UI may not display streaming responses properly. For full streaming experience, use the frontend application or a tool that supports SSE.

### Using curl

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "input": "Plan a 3-day trip to Tokyo",
    "session_id": "test_session"
  }' \
  --no-buffer
```

**Note:** Replace `YOUR_JWT_TOKEN` with a valid JWT token from Auth0. The `--no-buffer` flag ensures streaming output is displayed immediately.

---

## CORS Configuration

The application is configured to accept requests from Vite (port 5173) for frontend integration. To modify allowed origins, update the `allow_origins` parameter in `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Update as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Authentication & Authorization

### Auth0 Setup Requirements

1. **Create Auth0 Application**: Set up a Single Page Application (SPA) for the React frontend
2. **Create Auth0 API**: Configure an API with appropriate audience identifier
3. **Configure Roles**: Add custom roles (e.g., "user", "admin") to Auth0
4. **Set Role Namespace**: Configure custom claims namespace (e.g., `https://stateful-agent.com/roles`)

### Role-Based Access Control

- **User Role**: Required to access `/chat` endpoint
- **Token Validation**: JWT tokens are validated using Auth0's JWKS endpoint
- **Custom Claims**: The application checks for roles in the `https://stateful-agent.com/roles` claim

---

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'jose'**: 
   - Ensure you're using `uv run` to execute commands, or activate the virtual environment first
   - Run `uv sync` to install all dependencies
   - Verify that `python-jose[cryptography]>=3.3.0` is in your `pyproject.toml`

2. **Streaming Not Working**: Ensure the frontend client supports Server-Sent Events (SSE) or uses the Fetch API with ReadableStream

3. **Missing API Key Error**: Ensure your `.env` file contains a valid `GEMINI_API_KEY`

4. **Missing Auth0 Configuration**: Ensure `AUTH0_DOMAIN` and `API_AUDIENCE` are set in your `.env` file

5. **Import Errors**: Make sure all dependencies are installed with `uv sync`

6. **JWT Validation Errors**: Verify your Auth0 configuration and ensure tokens are valid and not expired

7. **Session Memory**: Each session maintains isolated memory - use the same `session_id` for related conversations

8. **CORS Errors**: Verify that the frontend origin is included in `allow_origins` in the CORS middleware configuration

9. **403 Forbidden Error**: Ensure your JWT token includes the required "user" role in the custom claims

10. **Langfuse Not Working**: 
    - Verify `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set in `.env`
    - Check that your Langfuse credentials are valid
    - The application will continue to work without Langfuse - observability features will simply be disabled
    - Check Langfuse dashboard for any authentication errors

---

## Key Implementation Details

- **Streaming Enabled**: LLM initialized with `streaming=True` for token-by-token generation
- **Async Streaming**: Uses `astream()` method for non-blocking async streaming in FastAPI
- **SSE Format**: Responses formatted as Server-Sent Events (`data: {content}\n\n`) for browser compatibility
- **StrOutputParser**: Converts LLM message chunks to strings for streaming
- **Memory Integration**: Streaming works seamlessly with `RunnableWithMessageHistory` for stateful conversations
- **Observability Integration**: Langfuse callback handler automatically tracks all LLM interactions with user and session context
- **Trace Flushing**: Langfuse traces are flushed at the end of each request and on application shutdown to ensure data is persisted

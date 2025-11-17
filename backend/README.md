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
- **JWT Authentication:** Secure Auth0 JWT token validation with JWKS (JSON Web Key Set) verification
- **CORS Enabled:** Configured for frontend integration with localhost:5173 (Vite)

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
```

**Important:** 
- Replace `your_gemini_api_key_here` with your actual Gemini API key
- Replace Auth0 configuration values with your actual Auth0 settings
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
├── security/            # Security module for JWT validation
│   ├── __init__.py     # Module initialization
│   └── security.py     # Auth0 JWT validation logic
├── .env                 # Environment variables (create with your API key and Auth0 config)
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

---

## How It Works

The application uses a **stateful conversational system with streaming and authentication**:

1. **Authentication Layer**: JWT tokens are validated before processing requests using FastAPI dependency injection
2. **LLM Setup**: Uses ChatOpenAI with Gemini API (configurable via .env) with `streaming=True` enabled
3. **Prompt Template**: Specialized travel assistant prompt with system instructions and conversation history placeholder
4. **Memory Store**: In-memory dictionary stores `ChatMessageHistory` objects per session
5. **LCEL Chain**: Combines prompt template with LLM and `StrOutputParser` using the `|` operator
6. **Stateful Wrapper**: `RunnableWithMessageHistory` automatically handles conversation context
7. **Session Management**: Each request includes a `session_id` that maps to a unique message history
8. **Streaming**: Uses `astream()` method to yield tokens asynchronously, wrapped in `StreamingResponse` with SSE format

### Authentication Flow

1. Client sends request with JWT token in `Authorization: Bearer <token>` header
2. FastAPI extracts token using `OAuth2PasswordBearer`
3. `validate_token` dependency validates token against Auth0 JWKS
4. If valid, request proceeds to endpoint handler
5. If invalid, HTTP 401 error is returned immediately

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

The application implements **JWT-based authentication** using Auth0, providing secure access control for protected endpoints. The authentication system validates tokens using industry-standard JWKS (JSON Web Key Set) verification.

### Authentication Implementation

The authentication system is implemented in the `security/security.py` module and uses FastAPI's dependency injection pattern:

1. **Token Extraction**: Uses `OAuth2PasswordBearer` to extract JWT tokens from the `Authorization: Bearer <token>` header
2. **JWKS Fetching**: Retrieves public keys from Auth0's JWKS endpoint (`https://{AUTH0_DOMAIN}/.well-known/jwks.json`)
3. **Key Caching**: Implements a 1-hour cache for JWKS to reduce API calls and improve performance
4. **Token Validation**: Validates JWT tokens by checking:
   - **Signature**: Verifies token signature using RSA public keys from JWKS
   - **Expiration**: Ensures token has not expired
   - **Audience**: Validates the `aud` claim matches `API_AUDIENCE`
   - **Issuer**: Validates the `iss` claim matches Auth0 domain
5. **Error Handling**: Returns appropriate HTTP 401 errors for invalid, expired, or malformed tokens

### Protected Endpoints

- **`/chat`**: Requires valid JWT token (authentication required)
- **`/new-session`**: Public endpoint (no authentication required)

### How Authentication Works

When a request is made to the `/chat` endpoint:

1. FastAPI extracts the token from the `Authorization` header using `OAuth2PasswordBearer`
2. The `validate_token` dependency function is called automatically
3. The function fetches (or uses cached) JWKS from Auth0
4. The token's header is parsed to find the key ID (`kid`)
5. The corresponding RSA public key is retrieved from JWKS
6. The token is decoded and validated against:
   - RSA public key (signature verification)
   - Expiration time
   - Audience claim
   - Issuer claim
7. If validation succeeds, the decoded token payload is returned
8. If validation fails, an HTTP 401 Unauthorized error is raised

### Code Implementation

The authentication is implemented using FastAPI's dependency injection:

```python
from security.security import validate_token

@app.post("/chat")
async def chat(payload: ChatInput, token_payload: dict = Depends(validate_token)):
    # token_payload contains the decoded JWT claims if validation succeeds
    # If validation fails, HTTPException(401) is raised automatically
    ...
```

The `validate_token` function in `security/security.py` handles all validation logic and returns the decoded token payload, which can be used to access user information or claims.

### Auth0 Setup Requirements

1. **Create Auth0 Application**: Set up a Single Page Application (SPA) for the React frontend
2. **Create Auth0 API**: Configure an API with appropriate audience identifier
3. **Get Configuration Values**: 
   - `AUTH0_DOMAIN`: Your Auth0 tenant domain (e.g., `your-tenant.auth0.com`)
   - `API_AUDIENCE`: The audience identifier for your Auth0 API
   - `ALGORITHMS`: Token signing algorithm (default: `RS256`)

### Request Format

All authenticated requests must include the JWT token in the Authorization header:

```http
Authorization: Bearer <your_jwt_token>
```

### Error Responses

The authentication system returns the following error responses:

- **401 Unauthorized**: 
  - Invalid token header
  - Token expired
  - Incorrect claims (audience/issuer mismatch)
  - Unable to parse token
  - Unable to find appropriate key in JWKS

All 401 responses include the `WWW-Authenticate: Bearer` header as per OAuth2 specification.

### Security Features

- **JWKS Caching**: Reduces Auth0 API calls with 1-hour cache (auto-refreshes on key rotation)
- **Automatic Key Rotation**: If a key is not found, the cache is refreshed once to handle key rotation
- **Secure Token Validation**: Uses RSA public key cryptography for signature verification
- **Standard Compliance**: Follows OAuth2 and JWT best practices

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

6. **JWT Validation Errors**: 
   - Verify your Auth0 configuration (`AUTH0_DOMAIN` and `API_AUDIENCE`) in `.env`
   - Ensure tokens are valid and not expired
   - Check that the token audience matches `API_AUDIENCE`
   - Verify the token issuer matches your Auth0 domain
   - Ensure the token signature is valid (JWKS keys are accessible)

7. **401 Unauthorized Errors**: 
   - Verify the token is included in the `Authorization: Bearer <token>` header
   - Check that the token format is correct
   - Ensure the token hasn't expired
   - Verify Auth0 JWKS endpoint is accessible: `https://{AUTH0_DOMAIN}/.well-known/jwks.json`

8. **Session Memory**: Each session maintains isolated memory - use the same `session_id` for related conversations

9. **CORS Errors**: Verify that the frontend origin is included in `allow_origins` in the CORS middleware configuration

---


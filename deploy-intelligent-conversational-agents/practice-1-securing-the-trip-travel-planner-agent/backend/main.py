# stateful_trip_agent.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel
import uuid
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
from security.security import validate_token
# -------------------------------
# Environment Setup
# -------------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL_NAME")
base_url = os.getenv("GEMINI_BASE_URL")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file.")
if not model_name:
    raise ValueError("GEMINI_MODEL_NAME not found in .env file.")
if not base_url:
    raise ValueError("GEMINI_BASE_URL not found in .env file.")
# -------------------------------
# Initialize FastAPI App
# -------------------------------
app = FastAPI(title="Stateful Travel & Trip Planner Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -------------------------------
# LLM Setup
# -------------------------------
llm = ChatOpenAI(
    model=model_name, 
    api_key=api_key, 
    base_url=base_url, 
    streaming=True)

# -------------------------------
# Prompt Template with Memory
# -------------------------------
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful travel assistant. Remember the user's trip details, activities, and preferences during this session."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}")
])

# -------------------------------
# Session Memory Store
# -------------------------------
store = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

# -------------------------------
# Core LCEL Chain
# -------------------------------
core_chain = prompt | llm | StrOutputParser()

# -------------------------------
# Wrap with Session-Based Memory
# -------------------------------
stateful_chain = RunnableWithMessageHistory(
    runnable=core_chain,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)

# -------------------------------
# FastAPI Endpoint
# -------------------------------

class ChatInput(BaseModel):
    input: str
    session_id: str

@app.get("/new-session")
def new_session():
    """Generate a new chat session ID."""
    return {"session_id": str(uuid.uuid4())}


## Task 3 - Protect the chat endpoint with JWT authentication.
@app.post("/chat")
async def route_query(data: ChatInput, token_payload: dict = Depends(validate_token)):
    """
    Protected endpoint. validate_token dependency will raise 401 if token invalid.
    token_payload is the decoded JWT payload.
    Admins are not allowed to access this endpoint. All other authenticated users can access.
    """
    # Role-based check: block admins, allow all other users
    roles_claim = token_payload.get("https://stateful-agent.com/roles", [])
    if roles_claim and "admin" in roles_claim:
        raise HTTPException(status_code=403, detail="Admin users are not allowed to access this endpoint.")


    config = {"configurable": {"session_id": data.session_id}}
    # ## CHANGED: Use async for and astream for true asynchronous streaming
    async def event_generator():
        try:
            # Use .astream() for non-blocking streaming in an async context
            async for chunk in stateful_chain.astream({"input": data.input}, config=config):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            # Log the full error for debugging
            print(f"Error during stream: {e}")
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")



# -------------------------------
# Run App
# -------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

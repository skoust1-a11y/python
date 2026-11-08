# stateful_trip_agent.py
import os
from typing import Any, Optional, Tuple
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnablePassthrough,RunnableBranch
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel
import uuid
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
from security.security import validate_token, get_user_email_from_auth0
from observability import observe, flush_langfuse
from callbacks.langfuse_callback import get_langfuse_manager
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

## Task 2 : Setup Langfuse callback handler and configure chain execution config
def setup_langfuse_callback(session_id: str, token_payload: dict) -> Tuple[dict, Optional[Any]]:
    """
    Setup Langfuse callback handler and configure chain execution config.
    
    Args:
        session_id: Session ID for trace grouping
        token_payload: Decoded JWT token payload
        
    Returns:
        Tuple of (config dict, callback_handler) where config is ready for chain execution
    """
    langfuse_manager = get_langfuse_manager()
    
    # Extract user email from token payload or fetch from Auth0 userinfo endpoint
    # Auth0 access tokens typically don't include email, so we fetch it from userinfo
    user_email = token_payload.get("email")
    
    if not user_email:
        raw_token = token_payload.get("_raw_token")
        if raw_token:
            user_email = get_user_email_from_auth0(raw_token)
    
    if not user_email:
        user_email = token_payload.get("sub")
    
    callback_handler = langfuse_manager.get_callback_handler(
        session_id=session_id,
        user_id=user_email,  # Use email as user identifier
        trace_name="chat",
    )
    
    config = {"configurable": {"session_id": session_id}}
    
    if callback_handler:
        config["callbacks"] = [callback_handler]
        config["metadata"] = {}
        if session_id:
            config["metadata"]["session_id"] = session_id
            config["metadata"]["langfuse_session_id"] = session_id
        if user_email:
            config["metadata"]["user_id"] = user_email
            config["metadata"]["langfuse_user_id"] = user_email
            config["metadata"]["user_email"] = user_email  # Also store as email for clarity
        # Add trace name and tags
        config["metadata"]["trace_name"] = "chat"
        config["metadata"]["langfuse_tags"] = ["chat"]
        
        # Also try setting metadata directly on the handler if supported
        if hasattr(callback_handler, 'set_trace_metadata'):
            try:
                callback_handler.set_trace_metadata(
                    session_id=session_id,
                    user_id=user_email,
                    trace_name="route_query"
                )
            except:
                pass
    
    return config, callback_handler


   


## Task 2:  Flush Langfuse traces. 
async def flush_langfuse_traces(callback_handler) -> None:
    """
    Flush Langfuse traces.
    """
    if not callback_handler:
        return

    try:
        client = None

        # Try to find the Langfuse client
        for attr in [
            "_explicit_langfuse_client",
            "_langfuse_client",
            "client",
            "langfuse",
            "_client",
            "langfuse_client",
        ]:
            if hasattr(callback_handler, attr):
                potential_client = getattr(callback_handler, attr)
                if potential_client and hasattr(potential_client, "flush"):
                    client = potential_client
                    break

        if not client:
            return

        # Flush pending traces first
        client.flush()

        import asyncio
        await asyncio.sleep(1.0)
    except Exception:
        pass

   

@app.get("/new-session")
def new_session():
    """Generate a new chat session ID."""
    return {"session_id": str(uuid.uuid4())}

@app.post("/chat")
async def chat(payload: ChatInput, token_payload: dict = Depends(validate_token)):
    """
    Stateful chat endpoint that remembers context per session.
    Streams the model's response token by token.
    """
       
    # Setup Langfuse callback handler and execution config (same pattern as demo-2)
    config, callback_handler = setup_langfuse_callback(payload.session_id, token_payload)

    async def event_generator():
        try:
            # Use .astream() for non-blocking streaming in an async context
            async for chunk in stateful_chain.astream({"input": payload.input}, config=config):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            # Log the full error for debugging
            print(f"Error during stream: {e}")
            yield f"data: Error: {str(e)}\n\n"
        finally:
            # Ensure traces are flushed at end of stream
            await flush_langfuse_traces(callback_handler)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.on_event("shutdown")
async def shutdown_event():
    """Flush Langfuse traces on application shutdown."""
    flush_langfuse()

# -------------------------------
# Run App
# -------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

from langchain_core.runnables import RunnableWithMessageHistory
from start.chat_history.inMemory import get_session_history
from start.orchestrators.supervisor import supervisor_runnable
from auth.jwt_validator import verify_jwt
from callbacks.langfuse_callback import get_langfuse_manager

# ---------------------------------------------------------------------------
# Router setup
# ---------------------------------------------------------------------------
router = APIRouter()

# ---------------------------------------------------------------------------
# Main Chain with History
# ---------------------------------------------------------------------------

# The stateful chain wraps the master supervisor agent directly
stateful_chain = RunnableWithMessageHistory(
    runnable=supervisor_runnable,
    get_session_history=get_session_history,
    input_messages_key='query',
    history_messages_key='chat_history'
)

# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str
    session_id: str

class ChatResponse(BaseModel):
    response: Any
    intent_detected: Optional[str] = "multi-step-workflow" # Hardcoded since the agent handles intents dynamically now

@router.post('/chat', response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, token_payload: dict = Depends(verify_jwt)):
    """
    Main conversational endpoint.
    Requires a valid Auth0 JWT in the Authorization header.
    """
    langfuse_handler = get_langfuse_manager().get_callback_handler(
        session_id=request.session_id,
        user_id=token_payload.get("sub", "unknown")
    )
    
    callbacks = [langfuse_handler] if langfuse_handler else []

    try:
        # Run the full stateful agent workflow
        result = stateful_chain.invoke(
            {"query": request.query},
            config={
                "configurable": {"session_id": request.session_id},
                "callbacks": callbacks
            }
        )

        return ChatResponse(
            response=result,
            intent_detected="multi-step-workflow"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
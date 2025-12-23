"""FastAPI application with endpoints for the support agent with checkpointing."""

import uuid
import uvicorn
from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from graph import build_graph
from schemas import MessageRequest, MessageResponse, ConversationStateResponse


app = FastAPI(
    title="Quick Commerce Support Agent API",
    description="API for demonstrating multi-turn conversations with checkpointing using LangGraph",
    version="0.1.0"
)


# Initialize graph (singleton pattern)
_graph = None


def get_graph():
    """
    Get or create the graph instance (singleton).
    
    TODO:
    1. Check if _graph is None
    2. If None, call build_graph() and cache in _graph
    3. Return _graph
    """
    # TODO: Implement get_graph function
    return None


@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest) -> MessageResponse:
    """
    Process a chat message through the multi-turn support agent graph.
    
    TODO:
    1. Get graph instance
    2. Generate thread_id if not provided
    3. Create config with thread_id
    4. Get current state from graph
    5. If first message, initialize state; else invoke with HumanMessage
    6. Convert messages to dict format
    7. Return MessageResponse with state and thread_id
    8. Handle exceptions
    """
    # TODO: Implement POST /chat endpoint
    raise HTTPException(status_code=501, detail="Not implemented")


@app.get("/conversation/{thread_id}", response_model=ConversationStateResponse)
async def get_conversation_state(thread_id: str) -> ConversationStateResponse:
    """
    Get the current state of a conversation by thread_id.
    
    TODO:
    1. Get graph instance
    2. Create config with thread_id
    3. Get state from checkpoint
    4. If state.values is None, raise 404
    5. Return ConversationStateResponse with state fields and message_count
    6. Handle exceptions
    """
    # TODO: Implement GET /conversation/{thread_id} endpoint
    raise HTTPException(status_code=501, detail="Not implemented")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

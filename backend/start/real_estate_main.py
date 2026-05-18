from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any,Tuple
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableWithMessageHistory, RunnableLambda
from start.chat_history.inMemory import get_session_history
from start.orchestrators.supervisor import supervisor_runnable
from callbacks.langfuse_callback import get_langfuse_manager
# from start.bots.fetch_locations import fetch_areas_runnable
from langchain_core.runnables import RunnableLambda,RunnableBranch
from start.bots.tools.fetch_opentrip_tool import fetch_tool,opentripmap_fetch,nearby_homes
from start.bots.tools.loc_tool import nominatim_geocode
from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder
from llm_machine.llm_setup import llm
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from callbacks.langfuse_callback import get_langfuse_manager
import uuid
from observability import flush_langfuse
from auth.jwt_validator import get_user_email_from_auth0,validate_token
from start.orchestrators.estate_orchestrator import orchestartor_LCEL
from langchain_core.prompts import ChatPromptTemplate
from start.bots.chains.location_chain import loc_parsing_chain
from start.bots.chains.location_chain import extract_place,area_spotter_chain,get_coordinates
from start.bots.tools.web_search_tool import web_search
from start.bots.estate_agent_basic import ai_agent_chain
from start.bots.chains.general_chain import general_chain
from start.bots.chains.neighbourhood_chain import neighbourhood_total_chain
from start.bots.tools.web_search_tool import property_search_tool

# ---------------------------------------------------------------------------
# Router setup
# ---------------------------------------------------------------------------
router = APIRouter()




def isLocation(input_type : dict) -> bool:
    classification : str = input_type.get('classification')
    if classification.strip().lower() == 'location_lookup':
        return True
    else:
        return False
def isProperty(input_type : dict) -> bool:
    classification : str = input_type.get('classification')
    if classification.strip().lower() == 'property_search':
        return True
    else:
        return False
def isAmenity(input_type : dict) -> bool:
    classification : str = input_type.get('classification')
    if classification.strip().lower() == 'amenity_search':
        return True
    else:
        return False
    
def isLifestyle(input_type : dict) -> bool:
    classification : str = input_type.get('classification')
    if classification.strip().lower() == 'lifestyle_match':
        return True
    else:
        return False




branchDecider = RunnableBranch(
    (isLocation,loc_parsing_chain),
    (isAmenity,neighbourhood_total_chain),
    (isLifestyle or isProperty,ai_agent_chain),
    general_chain
)



web_chain = web_search | StrOutputParser()



full_chain = orchestartor_LCEL | branchDecider




stateful_chain = RunnableWithMessageHistory(
    runnable=full_chain,
    get_session_history=get_session_history,
    input_messages_key='query',
    history_messages_key='chat_history'
)


# below code DONE outerpart  we need to build the LOGIC NOW.

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

   

@router.get("/new-session")
def new_session():
    """Generate a new chat session ID."""
    return {"session_id": str(uuid.uuid4())}

@router.post("/chat")
async def chat(payload: ChatInput, token_payload: dict = Depends(validate_token)):
    """
    Stateful chat endpoint that remembers context per session.
    Streams the model's response token by token.
    """
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

@router.on_event("shutdown")
async def shutdown_event():
    """Flush Langfuse traces on application shutdown."""
    flush_langfuse()



class TestInput(BaseModel):
    input: str

@router.post('/check')
def check(payload: TestInput):
    # response = property_search_tool.invoke({
    #     'query': payload.input
    # })
    # return response
    async def event_generator():
        try:
            # Use .astream() for non-blocking streaming in an async context
            async for chunk in full_chain.astream({"query": payload.input}):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            # Log the full error for debugging
            print(f"Error during stream: {e}")
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

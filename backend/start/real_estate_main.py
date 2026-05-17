from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any,Tuple
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableWithMessageHistory, RunnableLambda
from start.chat_history.inMemory import get_session_history
from start.orchestrators.supervisor import supervisor_runnable
from callbacks.langfuse_callback import get_langfuse_manager
from auth.jwt_validator import verify_jwt
from start.bots.fetch_locations import fetch_areas_runnable
from langchain_core.runnables import RunnableLambda,RunnableBranch
from start.bots.tools.fetch_opentrip_tool import fetch_tool,opentripmap_fetch
from start.bots.tools.loc_tool import nominatim_geocode
from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder
from llm_machine.llm_setup import llm
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from callbacks.langfuse_callback import get_langfuse_manager
import uuid
from observability import flush_langfuse
from auth.jwt_validator import get_user_email_from_auth0,validate_token
from start.orchestrators.estate_orchestrator import orchestartor_LCEL

# ---------------------------------------------------------------------------
# Router setup
# ---------------------------------------------------------------------------
router = APIRouter()




intent_prompt = ChatPromptTemplate.from_messages([
        ("system", """Classify user intent into one of:
        - location_lookup: User mentions a city/area
        - property_search: User asks for home recommendations
        - amenity_search: User asks about nearby facilities
        - commute_analysis: User asks about travel time
        - lifestyle_match: User asks for family/professional areas
        - general_conversation: Other queries"""),
        ("user", "{query}")
    ])

# branchDecider = RunnableBranch(
#     (isLocation,geo_loc_chain),
#     (isProperty,property_chain),
#     (isAmenity,amenity_chain),
#     (isCommute,commute_analysis_chain),
#     (isLifestyle,lifestyle_chain),
#     general_chain
# )


# location_agent_runnbale | 

# stateful_chain = RunnableWithMessageHistory(
#     runnable=full_chain,
#     get_session_history=get_session_history,
#     input_messages_key='query',
#     history_messages_key='chat_history'
# )

prompt = ChatPromptTemplate.from_messages([
    ('system', 'You are a City/Area/Region finder in a  user query.\n'
               'Respond to The User By Giving the only location related details found in the query and truncating the rest of the user query in a word/sentence.'),
    ('user', "Query : {original_query}")
])

area_spotter_chain = prompt | llm | StrOutputParser()


def loaction_trimmer(place: str):
    return place

extract_place = RunnableLambda(loaction_trimmer)


def get_coordinates(place):
    return nominatim_geocode.invoke({"place": place})


def get_nearby_places(coords):
    return fetch_tool.invoke(coords)


class AmenityScore(BaseModel):
    family_friendliness: int = Field(description="Score from 1-10")
    professional_convenience: int = Field(description="Score from 1-10")
    connectivity: int = Field(description="Score from 1-10")
    entertainment: int = Field(description="Score from 1-10")
    summary: str


parser = PydanticOutputParser(pydantic_object=AmenityScore)

amenity_score_prompt = ChatPromptTemplate.from_template(
    "Given these nearby amenities: {amenities}, score this neighborhood (1-10) for: "
    "family-friendliness, professional-convenience, connectivity, entertainment. "
    "Output JSON with scores and a summary." \
    "{format_instructions}"
)

neighborhood_chain = (
    opentripmap_fetch
    | amenity_score_prompt.partial(
        format_instructions=parser.get_format_instructions()
    )
    | llm
    | parser
)


# ---------------------------------------NeighBouhood Amenities List--------------------
dummy_chain = (
    area_spotter_chain
    | extract_place
    | RunnableLambda(get_coordinates)
    | opentripmap_fetch
)

# -----------------------------------------------------------------------------------


# ------------------Neighbourhood Amneties House Recommedatin Score-------------------
# dummy_chain = (
#     area_spotter_chain
#     | extract_place
#     | RunnableLambda(get_coordinates)
#     | neighborhood_chain
# )

# ---------------------------------------------------------





full_chain = orchestartor_LCEL | branchDecider # we will branch plz wait


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


@router.get('/check')
def check():
    response = dummy_chain.invoke({
        'original_query': 'I am in Nagole,Hyderabad'
    })
    result = response
    print(result, flush=True)
    print('-----------------')
    return result

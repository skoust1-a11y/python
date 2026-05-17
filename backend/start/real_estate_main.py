from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any

from langchain_core.runnables import RunnableWithMessageHistory, RunnableLambda
from start.chat_history.inMemory import get_session_history
from start.orchestrators.supervisor import supervisor_runnable
from callbacks.langfuse_callback import get_langfuse_manager
from auth.jwt_validator import verify_jwt
from start.bots.fetch_locations import fetch_areas_runnable
from start.bots.tools.fetch_opentrip_tool import fetch_tool, opentripmap_fetch
from start.bots.tools.loc_tool import nominatim_geocode
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from llm_machine.llm_setup import llm
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser

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
    intent_detected: Optional[str] = "multi-step-workflow"  # Hardcoded default


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(response=result, intent_detected=None)


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


# below code Just for demonstration purpose only


@router.get('/check')
def check():
    response = dummy_chain.invoke({
        'original_query': 'I am in Nagole,Hyderabad'
    })
    result = response
    print(result, flush=True)
    print('-----------------')
    return result

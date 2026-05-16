from fastapi import APIRouter
from langchain_core.runnables import RunnableWithMessageHistory
from start.orchestrators.estate_orchestrator import orchestartor_LCEL
from start.chat_history.inMemory import get_session_history
from langchain.agents import create_agent
from start.bots.location import location_agent_runnbale
from start.bots.fetch_locations import fetch_areas_runnable
from langchain_core.runnables import RunnableLambda
from start.bots.tools.fetch_opentrip_tool import fetch_tool,opentripmap_fetch
from start.bots.tools.loc_tool import nominatim_geocode
from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder
from llm_machine.llm_setup import llm
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel,Field
from langchain_core.output_parsers import PydanticOutputParser

router = APIRouter()

# full_chain = orchestartor_LCEL | branchDecider # we will branch plz wait


# location_agent_runnbale | 

# stateful_chain = RunnableWithMessageHistory(
#     runnable=full_chain,
#     get_session_history=get_session_history,
#     input_messages_key='query',
#     history_messages_key='chat_history'
# )







prompt = ChatPromptTemplate.from_messages([
    ('system','You are a City/Area/Region finder in a  user query.\n'
    'Respond to The User By Giving the only location related details found in the query and truncating the rest of the user query in a word/sentence.'),
    ('user',"Query : {original_query}")

])

area_spotter_chain = prompt | llm | StrOutputParser()


def loaction_trimmer(place : str):
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


#---------------------------------------NeighBouhood Amenities List--------------------
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

#---------------------------------------------------------


#below code Just for demonstration purpose only


@router.get('/check')
def check():
    response = dummy_chain.invoke({
        'original_query':'I am in Nagole,Hyderabad'
    })
    result = response
    print(result,flush=True)
    print('-----------------')
    return result
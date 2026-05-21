from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from llm_machine.llm_setup import llm
from langchain_core.runnables import RunnableWithMessageHistory, RunnableLambda
from start.bots.tools.loc_tool import nominatim_geocode
from start.bots.tools.fetch_opentrip_tool import fetch_tool, nearby_homes



prompt = ChatPromptTemplate.from_messages([
    ('system', 'You are a City/Area/Region finder in a  user query.\n'
               'Respond to The User By Giving the only exact location alone found in the query and truncating the rest of the user query in a word/sentence.'),
                MessagesPlaceholder(variable_name='chat_history'),
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

def nearby_homes_parser(my_dict : dict) -> str:
    return str(my_dict)


geo_loc_chain = (
    area_spotter_chain
    | extract_place
    | RunnableLambda(get_coordinates)
    | nearby_homes
    | RunnableLambda(nearby_homes_parser)
    | StrOutputParser()
)

def loc_summary(loc : str):
    return {
        'user_query' : loc
    }

loc_sum = RunnableLambda(loc_summary)


location_geo_lookup_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are a senior real-estate location intelligence assistant.

Your task is to analyze geo-location lookup results returned from external APIs and narrate meaningful real-estate insights.

Your job is to:
- Summarize residential ecosystem
- Narrate locality characteristics
- Infer urban density
- Mention apartment clusters
- Explain neighborhood quality
- Generate buyer/renter friendly insights
- Avoid raw JSON repetition
"""
    ),
    (
        "human",
        """
User Query:
{user_query}


Generate:
1. Location Overview
2. Residential Density Analysis
3. Nearby Residential Buildings
4. Neighborhood Insights
5. Real Estate Suitability Summary
"""
    )
])

loc_parsing_chain = geo_loc_chain | loc_sum | location_geo_lookup_prompt | llm | StrOutputParser()
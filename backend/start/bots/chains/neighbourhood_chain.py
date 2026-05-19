from pydantic import BaseModel,Field
from typing import Any,List,Dict
from langchain_core.output_parsers import PydanticOutputParser,StrOutputParser
from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder
from start.bots.tools.fetch_opentrip_tool import opentripmap_fetch
from llm_machine.llm_setup import llm
from start.bots.chains.location_chain import extract_place,area_spotter_chain,get_coordinates
from langchain_core.runnables import RunnableLambda,RunnableParallel




class AmenityScore(BaseModel):
    family_friendliness: int = Field(description="Score from 1-10")
    professional_convenience: int = Field(description="Score from 1-10")
    connectivity: int = Field(description="Score from 1-10")
    entertainment: int = Field(description="Score from 1-10")
    summary: str


parser = PydanticOutputParser(pydantic_object=AmenityScore)

amenity_score_prompt = ChatPromptTemplate.from_template("""
Nearby amenities:

{amenities}

Analyze this neighborhood.

Return:
- family_friendliness score
- professional_convenience score
- connectivity score
- entertainment score
- short summary
""")
structured_llm = llm.with_structured_output(AmenityScore)


neighborhood_chain_demo = (
    opentripmap_fetch
    | amenity_score_prompt.partial(
        format_instructions=parser.get_format_instructions()
    )
    | llm
    | parser
)


def simplify_amenities(data):
    simplified = {}

    for category, places in data["amenities"].items():
        simplified[category] = [
            {
                "name": place["properties"].get("name", "Unknown"),
                "distance_m": round(place["properties"].get("dist", 0), 2)
            }
            for place in places
        ]

    return {"amenities": simplified}


analysis_chain = (
    amenity_score_prompt
    | structured_llm
)
def merge_output(inputs):
    return {
        **inputs["analysis"].dict(),
        "amenities": inputs["amenities"]
    }

neighborhood_chain = (
    opentripmap_fetch
    | RunnableLambda(simplify_amenities)
    | RunnableParallel(
        amenities=RunnableLambda(lambda x: x["amenities"]),
        analysis=analysis_chain
    )
    | RunnableLambda(merge_output)
)


full_chain = (
    area_spotter_chain
    | extract_place
    | RunnableLambda(get_coordinates)
    | neighborhood_chain
)

chat_response_prompt = ChatPromptTemplate.from_template("""
You are a real estate neighborhood assistant.

Convert the following neighborhood analysis into a natural conversational response.

DATA:
{data}

Requirements:
- Friendly chatbot tone
- Mention top nearby amenities
- Mention distances naturally
- Mention strengths and weaknesses
- Keep response concise and readable
""")


response_chain = (
    chat_response_prompt
    | llm
    | StrOutputParser()
)

neighbourhood_total_chain = (
    full_chain
    | RunnableLambda(lambda x: {"data": x})
    | response_chain
)


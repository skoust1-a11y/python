from pydantic import BaseModel,Field
from typing import Any
from langchain_core.output_parsers import PydanticOutputParser,StrOutputParser
from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder
from start.bots.tools.fetch_opentrip_tool import opentripmap_fetch
from llm_machine.llm_setup import llm
from start.bots.chains.location_chain import extract_place,area_spotter_chain,get_coordinates
from langchain_core.runnables import RunnableLambda




class AmenityScore(BaseModel):
    family_friendliness: int = Field(description="Score from 1-10")
    professional_convenience: int = Field(description="Score from 1-10")
    connectivity: int = Field(description="Score from 1-10")
    entertainment: int = Field(description="Score from 1-10")
    summary: str
    amenities : Any


parser = PydanticOutputParser(pydantic_object=AmenityScore)

amenity_score_prompt = ChatPromptTemplate.from_template(
    "Given these nearby amenities: {amenities}, score this neighborhood (1-10) for: "
    "family-friendliness, professional-convenience, connectivity, entertainment. "
    "Output JSON String with scores, summary and given amenities data." 
)
structured_llm = llm.with_structured_output(AmenityScore)
# neighborhood_chain = (
#     opentripmap_fetch
#     | amenity_score_prompt.partial(
#         format_instructions=parser.get_format_instructions()
#     )
#     | llm
#     | parser
# )

neighborhood_chain = (
    opentripmap_fetch
    | amenity_score_prompt
    | structured_llm
)


neighbourhood_total_chain = (
    area_spotter_chain
    | extract_place
    | RunnableLambda(get_coordinates)
    | neighborhood_chain
    | StrOutputParser()
)
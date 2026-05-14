from langchain_core.prompts import ChatPromptTemplate
from llm_machine.llm_setup import llm
from langchain_core.output_parsers import StrOutputParser

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


classify_chain = intent_prompt | llm | StrOutputParser()




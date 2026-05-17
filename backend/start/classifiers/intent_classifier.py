from langchain_core.prompts import ChatPromptTemplate
from llm_machine.llm_setup import llm
from langchain_core.output_parsers import StrOutputParser

intent_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a classification assistant. Classify the user intent into EXACTLY ONE of the following categories, and output ONLY the category string:
location_lookup
property_search
amenity_search
commute_analysis
lifestyle_match
general_conversation

Do not output any other text."""),
        ("user", "{query}")
    ])


classify_chain = intent_prompt | llm | StrOutputParser()

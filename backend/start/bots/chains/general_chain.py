from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm_machine.llm_setup import llm


prompt = ChatPromptTemplate.from_messages([
    ('system', 'You are a General Assistant Chat Assistant for a user query.\n'
               'Respond to The User Accordingly.'),
    ('user', "Query : {original_query}")
]) 

general_chain = prompt | llm | StrOutputParser()
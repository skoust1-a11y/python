from langchain.agents import create_agent
from start.bots.tools.web_search_tool import web_search,property_search_tool,lifestyle_analysis_tool
from llm_machine.llm_setup import llm
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel,Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableLambda

# Step 1: Define JSON Schema
class PropertySearch(BaseModel):
    budget: str = Field(description="User property budget")
    location: str = Field(description="Preferred location")
    family_size: int = Field(description="Number of family members",default=4)
    property_type: str = Field(description="Type of property",default='homes')


# Step 2: JSON Parser
parser = PydanticOutputParser(pydantic_object=PropertySearch)


# Step 3: Prompt Template
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
        Extract the following details from the user query.

        Return ONLY valid JSON.

        {format_instructions}
        """
    ),
    (
        "user",
        "{original_query}"
    )
])


# Step 4: Partial Variables
final_prompt = prompt.partial(
    format_instructions=parser.get_format_instructions()
)


# Step 5: LCEL Chain
chain = final_prompt | llm | parser


prompt_template = ChatPromptTemplate.from_messages([
    (
        "system",
        """
        You are a helpful property finding assistant.
        
        Help users find suitable properties based on:
        - Budget
        - Location
        - Family Size
        """
    ),
    (
        "user",
        """
        Find me a {property_type} house.

        Budget: {budget}
        Location: {location}
        Family Size: {family_size}
        """
    )
])




prompt_chain_template = chain | prompt_template






agent_prompt = """
You are a real estate assistant.

RULES:
1. ALWAYS call a tool before answering property/lifestyle queries.
2. NEVER answer from memory.
3. NEVER suggest external portals manually.
4. Use:
   - property_search_tool for listings/prices
   - lifestyle_analysis_tool for area analysis
5. If no results:
   "No listings found right now."

Return concise structured responses.
"""
bunch_of_tools=[property_search_tool,lifestyle_analysis_tool]


estate_agent = create_agent(
    model=llm,
    system_prompt=agent_prompt,
    tools=bunch_of_tools,
    debug=True,
)


def handle_agent(input_dict: dict) -> str:
    """Handle agent-based queries using the agent"""
    query = input_dict.get('original_query', '')
    
    try:
        result = estate_agent.invoke(
            {"messages": [
                {"role": "user", "content": query}
                ]
            }
            )
        response = result['messages'][-1].content
        return str(response)
    except Exception as e:
        return f"Error processing location query: {str(e)}"

ai_agent_chain = RunnableLambda(handle_agent)
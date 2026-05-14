from llm_machine.llm_setup import llm
from langchain.agents import create_agent
from langchain_core.runnables import RunnableLambda
from start.bots.tools.loc_tool import nominatim_geocode

agent_prompt =  """You are a helpful latitude and longitude generator using given user city/area finding assistant.

        When users tells about his/her location:
        - FIRST: Find the user city/area from the query then Call nominatim_geocode to get the user's geographical latitude and longitude
        - THEN:Provide a structured Geographical latitude and longitiude in readable JSON FORMAT"""

tools = [nominatim_geocode]

location_agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt= agent_prompt,
    debug=True
)
def handle_location_query(input_dict: dict):
    """Handle location-based queries using the agent"""
    query = input_dict.get('original_query', '')
    
    try:
        result = location_agent.invoke(
            {"messages": [
                {"role": "user", "content": query}
                ]
            }
            )
        response = result['messages'][-1].content
        return response
    except Exception as e:
        return f"Error processing location query: {str(e)}"

location_agent_runnbale = RunnableLambda(handle_location_query)
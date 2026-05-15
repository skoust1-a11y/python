from llm_machine.llm_setup import llm
from langchain.agents import create_agent
from langchain_core.runnables import RunnableLambda
from start.bots.tools.fetch_opentrip_tool import fetch_tool
import json

agent_prompt =  """You are a helpful nearby areas fetching assistant using given latitiude and longitude co-ordinates.

        When users tells about his/her latitude and logitude:
        - FIRST: Find the user nearby areas from the query then Call fetch_tool to get the user's nearby places
        - THEN:Provide a structured data in readable JSON FORMAT"""




tools = [fetch_tool]

fetch_areas_agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt= agent_prompt,
    debug=True
)
def handle_places_query(query: str):
    """Handle nearby locations resulting by given queries using the agent"""
    # query = input_dict.get('original_query', '')
    
    try:
        result = fetch_areas_agent.invoke(
            {"messages": [
                {"role": "user", "content": query}
                ]
            }
            )
        response = result['messages'][-1].content
        cleaned = response.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)
        return data
    except Exception as e:
        return f"Error processing location query: {str(e)}"

fetch_areas_runnable = RunnableLambda(handle_places_query)
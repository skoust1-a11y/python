from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda

from llm_machine.llm_setup import llm
from start.bots.tools.loc_tool import nominatim_geocode
from start.bots.tools.fetch_opentrip_tool import fetch_tool
from start.bots.tools.fetch_homes import fetch_homes

# ---------------------------------------------------------------------------
# Master Supervisor Agent Prompt
# ---------------------------------------------------------------------------
supervisor_prompt_text = """You are an elite, AI-powered Real Estate Assistant.
Your goal is to help users find suitable homes, compare neighborhoods, evaluate commute preferences, and provide lifestyle-matched suggestions.

You have access to the following tools:
1. `nominatim_geocode`: Converts a city or neighborhood name into Latitude and Longitude.
2. `fetch_tool` (OpenTripMap): Fetches nearby amenities (schools, hospitals, transit) given Lat/Lon.
3. `fetch_homes` (Overpass): Finds residential buildings and apartments given Lat/Lon.

WORKFLOW INSTRUCTIONS:
- If a user asks for homes in a specific area, YOU MUST FIRST use `nominatim_geocode` to get coordinates.
- THEN, use `fetch_homes` with those coordinates.
- If they ask for nearby amenities (like schools), use `fetch_tool` with the coordinates.
- When presenting properties, you MUST use the exact following format for EACH property:

Option [number]:
[Property Name] ([Building Type]) - [Short description of the property].
--list of nearby amenities
--schools
--sightseeings,etc
--add something like nearest metro station , railway station or transport connectivity
--any other thing which user requested

- Do not show raw JSON to the user.
- Remember user preferences from the chat history."""

# ---------------------------------------------------------------------------
# Agent Setup
# ---------------------------------------------------------------------------
tools = [nominatim_geocode, fetch_tool, fetch_homes]

master_agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=supervisor_prompt_text,
)

# ---------------------------------------------------------------------------
# Runnable Wrapper
# ---------------------------------------------------------------------------
def execute_workflow(input_dict: dict) -> str:
    """Invokes the supervisor agent with the given query and history."""
    try:
        query = input_dict.get("query", "")
        # The custom create_agent expects a "messages" key
        result = master_agent.invoke({
            "messages": [
                {"role": "user", "content": query}
            ]
        })
        return result['messages'][-1].content
    except Exception as e:
        return f"System error during agent execution: {str(e)}"

supervisor_runnable = RunnableLambda(execute_workflow)

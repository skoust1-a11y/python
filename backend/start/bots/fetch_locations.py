from llm_machine.llm_setup import llm
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from start.bots.tools.fetch_opentrip_tool import fetch_tool
import json

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful nearby-places assistant.\n\n"
        "Given a latitude and longitude, you:\n"
        "1. Call the `fetch_tool` to retrieve nearby places of interest "
        "(schools, hospitals, parks, malls, gyms, public transport).\n"
        "2. Summarize and return the results as structured JSON.",
    ),
    MessagesPlaceholder("chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

# ---------------------------------------------------------------------------
# Agent + Executor
# ---------------------------------------------------------------------------

_tools = [fetch_tool]

_fetch_areas_agent = create_tool_calling_agent(
    llm=llm,
    tools=_tools,
    prompt=_prompt,
)

_fetch_areas_executor = AgentExecutor(
    agent=_fetch_areas_agent,
    tools=_tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=4,
)

# ---------------------------------------------------------------------------
# Runnable wrapper
# ---------------------------------------------------------------------------

def _handle_places_query(query: str) -> dict:
    """Invoke the nearby-places agent; accepts a plain string query."""
    try:
        result = _fetch_areas_executor.invoke({"input": query})
        output = result.get("output", "{}")
        cleaned = output.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"result": cleaned}
    except Exception as e:
        return {"error": f"Error fetching nearby places: {str(e)}"}


fetch_areas_runnable = RunnableLambda(_handle_places_query)
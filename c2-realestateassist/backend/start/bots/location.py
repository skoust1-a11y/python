# from llm_machine.llm_setup import llm
# from langchain.agents import create_tool_calling_agent, AgentExecutor
# from langchain_core.runnables import RunnableLambda
# from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from start.bots.tools.loc_tool import nominatim_geocode

# # ---------------------------------------------------------------------------
# # Prompt
# # ---------------------------------------------------------------------------

# _prompt = ChatPromptTemplate.from_messages([
#     (
#         "system",
#         "You are a helpful location assistant that converts user-mentioned city/area names "
#         "into geographic coordinates (latitude and longitude).\n\n"
#         "Instructions:\n"
#         "1. Extract the city or area name from the user's message.\n"
#         "2. Call the `nominatim_geocode` tool with that place name.\n"
#         "3. Return the result as structured JSON with 'lat' and 'lon' keys.",
#     ),
#     MessagesPlaceholder("chat_history", optional=True),
#     ("human", "{input}"),
#     MessagesPlaceholder("agent_scratchpad"),
# ])

# # ---------------------------------------------------------------------------
# # Agent + Executor
# # ---------------------------------------------------------------------------

# _tools = [nominatim_geocode]

# _location_agent = create_tool_calling_agent(
#     llm=llm,
#     tools=_tools,
#     prompt=_prompt,
# )

# _location_agent_executor = AgentExecutor(
#     agent=_location_agent,
#     tools=_tools,
#     verbose=True,
#     handle_parsing_errors=True,
#     max_iterations=4,
# )

# # ---------------------------------------------------------------------------
# # Runnable wrapper
# # ---------------------------------------------------------------------------

# def _handle_location_query(input_dict: dict) -> str:
#     """Invoke the location agent; accepts a dict with 'original_query' key."""
#     query = input_dict.get("original_query", "") if isinstance(input_dict, dict) else str(input_dict)
#     try:
#         result = _location_agent_executor.invoke({"input": query})
#         return result.get("output", "")
#     except Exception as e:
#         return f"Error processing location query: {str(e)}"


# location_agent_runnable = RunnableLambda(_handle_location_query)
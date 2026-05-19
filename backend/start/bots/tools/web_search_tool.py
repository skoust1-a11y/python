


from langchain.tools import tool
import requests
import json
from pydantic import BaseModel
from tavily import TavilyClient
from settings.env_config import config

if not config.require_env('WEB_SEARCH_TAVILY'):
    raise ValueError('TAVILY API KEY NOT FOUND')


class QueryModel(BaseModel):
    query : str 


@tool(args_schema=QueryModel)
def web_search(query: str):
    """
    web search
    """
    client = TavilyClient(config.require_env('WEB_SEARCH_TAVILY'))

    response = client.search(
    query=query,
    search_depth="advanced",
    max_results=5
    )
    results = response.get("results", [])

    combined_text = "\n---------------------------\n".join(
        [r.get("content", "") for r in results]
    )

    return combined_text


@tool(args_schema=QueryModel)
def property_search_tool(query: str):
    """
    Use this tool whenever the user asks:
    - property listings
    - BHK apartments
    - villas
    - homes for sale/rent
    - property prices
    - properties under a budget

    Input must be the EXACT user query.
    """

    client = TavilyClient(config.require_env('WEB_SEARCH_TAVILY'))
    
    tavily_query = f"""
    site:99acres.com OR site:magicbricks.com OR site:housing.com
    {query}
    """

    response = client.search(
        query=tavily_query,
        search_depth="advanced",
        max_results=20   
    )

    results = response.get("results", [])

    # Filter only results that likely have property names
    filtered = [ ]

    if not filtered:
        filtered = results  # fallback to all results

    combined_text = "\n---------------------------\n".join(
        [
            f"Source: {r.get('url', '')}\n{r.get('content', '')}"
            for r in filtered
        ]
    )

    return combined_text

@tool(args_schema=QueryModel)
def lifestyle_analysis_tool(query: str):
    """
    Analyze residential areas based on lifestyle suitability.
    """

    tavily_query = f"""
    Best residential areas for:
    {query}

    Include:
    - Family friendliness
    - Connectivity
    - Safety
    - Nearby amenities
    - Lifestyle score
    """

    client = TavilyClient(config.require_env("WEB_SEARCH_TAVILY"))

    response = client.search(
        query=tavily_query,
        search_depth="advanced",
        max_results=5
    )

    results = response.get("results", [])

    if not results:
        return "No lifestyle data found."

    summaries = []

    for r in results:
        content = r.get("content", "")[:500]

        summaries.append(content)

    final_summary = "\n\n".join(summaries)

    return f"""
    Lifestyle Analysis Result:

    {final_summary}
    """


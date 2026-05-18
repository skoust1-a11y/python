


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
        max_results=7   
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
    Analyzes residential locations based on lifestyle suitability,
    amenities, connectivity, safety, and living standards.

    This tool is useful for identifying:
    - Family-friendly areas
    - Professional-friendly areas
    - Budget-friendly zones
    - Luxury residential zones
    """

    tavily_query = f"""
    Analyze the best residential areas for the following user requirement:

    User Query:
    {query}

    Provide a structured lifestyle analysis covering:

    1. Family-friendly areas
       - Good schools
       - Parks
       - Hospitals
       - Safety
       - Peaceful environment

    2. Professional-friendly areas
       - Near IT hubs
       - Office connectivity
       - Metro/public transport
       - Coworking spaces
       - Traffic conditions

    3. Budget-friendly zones
       - Affordable housing
       - Low rent/property prices
       - Daily living affordability
       - Public transport access

    4. Luxury zones
       - Premium gated communities
       - High-end apartments/villas
       - Shopping malls
       - Fine dining
       - Premium lifestyle amenities

    Also include:
    - Nearby amenities
    - Connectivity
    - Popular landmarks
    - Overall lifestyle suitability summary
    """


    client = TavilyClient(config.require_env('WEB_SEARCH_TAVILY'))


    response = client.search(
    query=tavily_query,
    search_depth="advanced",
    max_results=5
    )
    results = response.get("results", [])

    combined_text = "\n---------------------------\n".join(
        [r.get("content", "") for r in results]
    )

    return combined_text


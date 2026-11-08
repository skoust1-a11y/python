# travel_tools.py
"""
Implements:
- Internal Tool: get_destination_info
- External Tool: get_user_location (via apiip.net)
"""


import os
from typing import List,Optional
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from pydantic import BaseModel,Field,ValidationError
from dotenv import load_dotenv
import json
from langchain.messages import HumanMessage,SystemMessage,AIMessage
from langchain_core.output_parsers import PydanticOutputParser  
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.exceptions import LangChainException,OutputParserException
import requests

# -------------------------------
# Environment Setup
# -------------------------------
load_dotenv()
API_KEY = os.getenv("APIIP_API_KEY")  # Ensure correct variable name in .env file
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL=os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
GEMINI_MODEL_NAME=os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set")

# -------------------------------
# LLM Initialization
# -------------------------------
llm = ChatOpenAI(
    api_key=GEMINI_API_KEY,
    base_url=GEMINI_BASE_URL,
    model=GEMINI_MODEL_NAME,
)

# -------------------------------
# Task 1: Internal Tool (LLM-powered)
# -------------------------------
#Implement a tool function that validates the destination input, invokes the LLM with a travel 
# prompt, and returns structured JSON with destination info or error messages.
class DestinationInput(BaseModel):
    destination : str = Field(min_length=2)
class TripPlanOutput(BaseModel):
    months : int
    attractions : List
    notable_features : str

@tool
def get_destination_info(dest : DestinationInput) -> str:
    """
    Generates a structured trip plan for a given destination using an LLM.
    Validates the input, invokes the LLM with a travel prompt, and returns a JSON object with:
      - months (int): Number of recommended months to visit
      - attractions (List): List of main attractions
      - notable_features (str): Other notable features
    Returns error messages in JSON if validation or LLM fails.
    """
    try:
        parser = PydanticOutputParser(pydantic_object=TripPlanOutput)
        format_instructions= parser.get_format_instructions()
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a Travel Agent. Respond in valid JSON format.\n{format_instructions}"),
            ("human", "Generate a trip plan for {destination} and generalize the months, attractions, and other notable features.")
        ])
        format_prompt = prompt_template.format_messages(
            destination = dest.destination,
            format_instructions = format_instructions
        )
        response = llm.invoke(format_prompt)
        return parser.parse(response.content).model_dump_json()
    
    except ValidationError as e:
        return json.dumps({"error": f'Pydantic Error {str(e)}'})
    except LangChainException as e:
            return json.dumps({"error": f'LLM Error: {str(e)}'})
    except OutputParserException as e:
        return json.dumps({"error": f'Parsing Error: {str(e)}'})
    except KeyError as e:
        return json.dumps({"error": f'Prompt Placeholder Error: {str(e)}'})
    except Exception as e:
        return json.dumps({"error": f'Server Error: {str(e)}'})


# -------------------------------
# Task 2: External Tool
# -------------------------------

#Implement a tool function that validates the API key, calls the external apiip.net service, 
# handles network errors, and returns user location data in JSON format
class LocationModel(BaseModel):
    ip : str
    city : str
    region : str
    country : str
class LocationInput(BaseModel):
    """
    Dummy input model for location tool compatibility with agent frameworks.
    """
    query: Optional[str] = Field(default="fetch_location", description="Dummy field; not used.")
@tool
def get_user_location(dummy_input: LocationInput) -> str:
    """
    Fetches the user's geographical location using the apiip.net service.
    Validates the API key, calls the external API, and returns a JSON object with:
      - ip (str): User's IP address
      - city (str): City name
      - region (str): Region name
      - country (str): Country name
    Returns error messages in JSON if the API key is missing or a network/server error occurs.
    """
    APIIP_API_KEY = os.getenv("APIIP_API_KEY")
    if not APIIP_API_KEY:
        return json.dumps({"error": "MIssing Geo Env: API key for apiip.net is missing or invalid."})

    url = f"http://apiip.net/api/check?accessKey={APIIP_API_KEY}"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        # location_info = {
        #     "ip": data.get("ip"),
        #     "city": data.get("city"),
        #     "region": data.get("regionName"),
        #     "country": data.get("countryName"),
        # }
        location_info = LocationModel(
        city=data.get('city') or "Unknown City",
        country=data.get('countryName') or "Unknown Country",
        ip=data.get('ip') or "Unknown IP",
        region=data.get('regionName') or "Unknown Region"
        )
        # location_info = LocationModel(city=data.get('city'),country=data.get('countryName'),ip=data.get('ip'),region=data.get('regionName'))
        return location_info.model_dump_json()
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Network error fetching location: {e}"})
    except Exception as e:
        return json.dumps({"error":f"Server error: {e}"})

import json
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from travel_tools import get_destination_info, get_user_location
import os
import uvicorn
# -------------------------------
# Environment Setup
# -------------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL=os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
GEMINI_MODEL_NAME=os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set")

app = FastAPI(title="Travel & Trip Planner Bot", version="4.0")

# -------------------------------
# Initialize LLM (Gemini)
# -------------------------------
model = ChatOpenAI(
    base_url=GEMINI_BASE_URL,
    model=GEMINI_MODEL_NAME,
    api_key=GEMINI_API_KEY,
    temperature=0.3,
)


# -------------------------------
# Step 2: Setup with Tools
# -------------------------------



# -------------------------------
# Step 3: Create Agent
# -------------------------------
prompt= """You are a helpful travel and trip planning assistant. 
When users ask about places to visit near them, places near their location, or visiting places in their area:
   - FIRST: Automatically call get_user_location to get the user's city/region
   - THEN: Automatically call get_destination_info with the user's city name (extracted from location) to get travel information
   - DO NOT ask follow-up questions - directly provide the information using both tools
"""
# Create an Agent using create_agent with the prompt and tools



# -------------------------------
# ROUTES
# -------------------------------
# Task -1 Test internal tool
# Create an endpoint (`/tools/internal`) and call the get_destination_info tool.
#Implement a FastAPI route that calls the internal LangChain tool get_destination_info, parses its output,
# and handles exceptions with HTTP errors.


# Task -2 External Tool Test
# Create an endpoint (`/tools/external`) and call the get_user_location tool.
#Implement a FastAPI route that calls the get_user_location LangChain tool, parses the JSON response, 
#and handles any exceptions with HTTP errors



# Task-3 Intelligent Agent Endpoint
# Create an endpoint (`/ask`) which will accept input from user and invoke the agent.


# -------------------------------
# Run Server
# -------------------------------
if __name__ == "__main__":
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    
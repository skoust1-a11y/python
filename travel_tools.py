# travel_tools.py
"""
Implements:
- Internal Tool: get_destination_info
- External Tool: get_user_location (via apiip.net)
"""


import os
from langchain_openai import ChatOpenAI

from dotenv import load_dotenv


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


# -------------------------------
# Task 2: External Tool
# -------------------------------

#Implement a tool function that validates the API key, calls the external apiip.net service, 
# handles network errors, and returns user location data in JSON format
"""
Sprint 3 Solution — Travel & Trip Planner Agent
LangChain + FastAPI + ChatOpenAI (via langchain_openai)

Implements:
  • Task 1: Fetch Prompt from Langfuse
  • Task 2: Few-Shot Prompting with ChatPromptTemplate.from_messages()
  • Task 3: Structured Output with PydanticOutputParser
"""

import os
from typing import List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError


# LangChain imports


# -------------------------------------------------------------------
# Load environment
# -------------------------------------------------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
if not GEMINI_API_KEY:
    raise RuntimeError("Please set GEMINI_API_KEY in your .env file.")

# -------------------------------------------------------------------
# Initialize FastAPI app
# -------------------------------------------------------------------
app = FastAPI(title="Travel Planner Advanced - Sprin 3")
#-------------------------------------------------------------------
# Initialize the Langfuse client using environment variables for public key, secret key, and host URL
#-------------------------------------------------------------------


# -------------------------------------------------------------------
# Helper: initialize LLM client
# -------------------------------------------------------------------
llm= ChatOpenAI(
        model=GEMINI_MODEL_NAME,
        api_key=GEMINI_API_KEY,
        base_url=GEMINI_BASE_URL,
        temperature=0.3,
        max_retries=2,
    )

# -------------------------------------------------------------------
# Task 1 — Fetch Prompt from Langfuse
# -------------------------------------------------------------------
#Define a Pydantic model to capture itinerary request details: destination, number of days, and budget

#Implement an async FastAPI route that retrieves a production prompt from Langfuse, replaces placeholders with user 
# data, invokes the LLM, and returns the response, handling errors if the prompt is missing

# -------------------------------------------------------------------
# Task 2 — Few-Shot Prompting with ChatPromptTemplate.from_messages()
# -------------------------------------------------------------------

#Define a Pydantic model UserQuery to capture the user’s input query for processing

# Create a POST endpoint /task2 that uses few-shot prompting with ChatPromptTemplate to generate a day-by-day travel itinerary 
# from a user query

# -------------------------------------------------------------------
# Task 3 — Structured Output Parsing (PydanticOutputParser)
# -------------------------------------------------------------------
# Define Pydantic schema for validated output
class TripPlan(BaseModel):
    destination: str = Field( 
        min_length=1,
        description="Travel destination")
    days: int = Field( 
        ge=1,
        le=30,
        description="Number of days for the trip")
    estimated_cost: str = Field( 
        min_length=1,
        description="Estimated total cost for the trip")
    highlights: List[str] = Field( 
        min_items=1,
        max_items=10,
        description="Top highlights of the destination")

class TripPlanRequest(BaseModel):
    destination: str 
    days: int 
    budget: int 

#Implement an async FastAPI route that formats a prompt with ChatPromptTemplate, invokes the LLM, 
# parses the response with PydanticOutputParser, and handles validation or general errors gracefully.

    

# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("travel_planner_advanced:app", host="0.0.0.0", port=8000, reload=True)

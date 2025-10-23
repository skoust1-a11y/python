# main.py
import json
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.prompts import ChatPromptTemplate
from travel_tools import get_destination_info, get_user_location
import os

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
llm = ChatOpenAI(
    base_url=GEMINI_BASE_URL,
    model=GEMINI_MODEL_NAME,
    api_key=GEMINI_API_KEY,
    temperature=0.3,
)

# -------------------------------
# Agent Setup with Tools
# -------------------------------
#Create a LangChain agent with multiple tools, specifying ZERO_SHOT_REACT_DESCRIPTION as the agent type
# and enabling verbose output for debugging.




# -------------------------------
# ROUTES
# -------------------------------
# Task -1 Test internal tool

#Implement a FastAPI route that calls the internal LangChain tool get_destination_info, parses its output,
# and handles exceptions with HTTP errors.


# Task -2 External Tool Test

#Implement a FastAPI route that calls the get_user_location LangChain tool, parses the JSON response, 
#and handles any exceptions with HTTP errors



# Task-3 Intelligent Agent Endpoint

#Implement a FastAPI route where the LangChain agent evaluates the input query, invokes the appropriate tool,
#and returns structured output while handling exceptions


# -------------------------------
# Run Server
# -------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    
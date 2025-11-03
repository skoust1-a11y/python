import json
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from travel_tools import get_destination_info, get_user_location
import os
from langchain import hub
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
# Step 3: Define Prompt
# -------------------------------
# Replace your custom prompt with the recommended one from the hub.
# This prompt is specifically designed to work with the ReAct agent.
#Use the non-conversational ReAct prompt that does not require `chat_history`.



# -------------------------------
# Step 4: Create ReAct Agent
# -------------------------------
# Create a ReAct Agent
# Create an AgentExecutor with the agent and tools


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
# Create an endpoint (`/ask`) which will accept input from user and invoke the agent executor.


# -------------------------------
# Run Server
# -------------------------------
if __name__ == "__main__":
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    
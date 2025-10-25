# stateful_trip_agent.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from pydantic import BaseModel
import uuid
# -------------------------------
# Environment Setup
# -------------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file.")

# -------------------------------
# Initialize FastAPI App
# -------------------------------
app = FastAPI(title="Stateful Travel & Trip Planner Agent")

# -------------------------------
# LLM Setup
# -------------------------------
llm = ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url)

# -------------------------------
# Prompt Template with Memory
# -------------------------------


# -------------------------------
# Session Memory Store
# -------------------------------
store = {}

#Create a function get_session_history that returns a unique ChatMessageHistory for each session,
# initializing it if it doesn’t already exist, to enable session-specific short-term memory in the agent.


# -------------------------------
# Core LCEL Chain
# -------------------------------
core_chain = prompt | llm

# -------------------------------
# Wrap with Session-Based Memory
# -------------------------------
# Wrap the core_chain with RunnableWithMessageHistory to make it stateful, 
# enabling the agent to track and recall conversation history per session using the get_session_history function.


# -------------------------------
# FastAPI Endpoint
# -------------------------------

class ChatInput(BaseModel):
    input: str
    session_id: str

#Create a FastAPI endpoint /new-session that generates and returns a unique session ID for each new chat,
# enabling session-based memory tracking.

# Create a FastAPI /chat endpoint that accepts user input and session ID, invokes the stateful_chain to maintain conversation context, 
# and returns the session ID, user input, and agent’s response.

# -------------------------------
# Run App
# -------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("stateful_trip_agent:app", host="0.0.0.0", port=8000)

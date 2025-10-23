import os
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableBranch

# Load environment
load_dotenv()

# Initialize LLM
llm = ChatOpenAI(
    model=os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash"),
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url=os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
)

# -------------------------------
# Step 1: Intent Classification
# -------------------------------
intent_prompt = ChatPromptTemplate.from_messages([
    ("system", "Classify this travel-related query as one of the following:\n"
               "- BOOKING: user wants to book/reserve a trip, hotel, or flight.\n"
               "- CANCELLATION: user wants to cancel or change an existing booking.\n"
               "- GENERAL: user is asking about travel info or suggestions.\n"
               "Respond with only one word: BOOKING, CANCELLATION, or GENERAL."),
    ("user", "{query}")
])


# -------------------------------
# Step 2: Condition Functions
# -------------------------------


# -------------------------------
# Step 3: Branch Chains
# -------------------------------


# -------------------------------
# Step 4: Router
# -------------------------------

# -------------------------------
# Step 5: Orchestration
# -------------------------------


# -------------------------------
# Step 6: FastAPI Setup
# -------------------------------


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("travel_router:app", host="0.0.0.0", port=8000)

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema.output_parser import StrOutputParser
from langchain_core.runnables import RunnableLambda

# -------------------------------
# Environment setup
# -------------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

if not api_key:
    raise ValueError("GEMINI_API_KEY is not set. Please configure it in your .env file.")

# Initialize LLM
llm = ChatOpenAI(
    model=model_name,
    api_key=api_key,
    base_url=base_url
)

# -------------------------------
# Step 1: Sentiment Classification Prompt
# -------------------------------


# -------------------------------
# Step 2: Urgency Classification Function
# -------------------------------


# -------------------------------
# Step 3: Response Strategy Prompt
# -------------------------------


# -------------------------------
# Step 4: Full LCEL Chain
# -------------------------------


# -------------------------------
# Step 5: FastAPI Setup
# -------------------------------
app = FastAPI(title="Travel Feedback Analyzer - LCEL")

class FeedbackInput(BaseModel):
    feedback: str




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("feedback_chain:app", host="0.0.0.0", port=8000)

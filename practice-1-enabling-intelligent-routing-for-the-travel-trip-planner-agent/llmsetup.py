from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

if not api_key:
    raise ValueError("GEMINI_API_KEY is not set. Please configure it in your .env file.")
if not base_url:
    raise ValueError("GEMINI_BASE_URL is not set. Please configure it in your .env file.")


# Initialize LLM
llm = ChatOpenAI(
    model=model_name,
    api_key=api_key,
    base_url=base_url
)

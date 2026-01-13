from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
from tools.tools import search_web, calculate
import os

load_dotenv()

# Azure OpenAI configuration
azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_model = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini")
azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# Base LLM (for planning, verification, replanning)
llm = AzureChatOpenAI(
    api_key=azure_api_key,
    azure_endpoint=azure_endpoint,
    model=azure_model,
    api_version=azure_api_version,
    temperature=0,
)

# LLM with tools bound (for execution phase only)
llm_with_tools = llm.bind_tools([
    search_web,
    calculate
])

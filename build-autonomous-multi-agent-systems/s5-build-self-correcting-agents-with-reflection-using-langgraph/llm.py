# TODO: Initialize Azure OpenAI LLM
# 
# INSTRUCTIONS:
# 1. Load environment variables using `load_dotenv()`
# 
# 2. Get the required environment variables:
#    - AZURE_OPENAI_API_KEY
#    - AZURE_OPENAI_ENDPOINT
#    - AZURE_OPENAI_API_VERSION
#    - AZURE_OPENAI_DEPLOYMENT_NAME (or MODEL_NAME)
# 
# 3. Initialize `AzureChatOpenAI` with:
#    - api_key
#    - azure_endpoint
#    - api_version
#    - azure_deployment (or validation logic)
#    - temperature=0
#    - max_retries=3
#    - timeout=60
# 
# 4. Export the instance as `llm`

import os
from dotenv import load_dotenv
from langchain_openai.chat_models.azure import AzureChatOpenAI

load_dotenv()

api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or os.getenv("MODEL_NAME")

if not api_key:
    raise ValueError("AZURE_OPENAI_API_KEY is required")
if not azure_endpoint:
    raise ValueError("AZURE_OPENAI_ENDPOINT is required")
if not api_version:
    raise ValueError("AZURE_OPENAI_API_VERSION is required")
if not deployment_name:
    raise ValueError("AZURE_OPENAI_DEPLOYMENT_NAME or MODEL_NAME is required")

llm = AzureChatOpenAI(
    api_key=api_key,
    azure_endpoint=azure_endpoint,
    api_version=api_version,
    azure_deployment=deployment_name,
    max_retries=3,
    temperature=0,
    timeout=60,
)

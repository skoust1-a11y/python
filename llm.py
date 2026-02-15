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

llm = None

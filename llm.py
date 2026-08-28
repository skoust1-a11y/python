from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
from tools.tools import search_web, calculate
import os
import time

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

def invoke_with_retry(llm_instance, messages, max_retries=3, retry_delay=5):
    """Invoke LLM with manual retry handling for rate limits and connection timeouts."""
    import logging
    logger = logging.getLogger(__name__)
    
    for attempt in range(max_retries + 1):
        try:
            return llm_instance.invoke(messages)
        except Exception as e:
            error_str = str(e).lower()
            error_type = type(e).__name__
            
            # Check for rate limit errors (429 or rate limit in message)
            is_rate_limit = (
                "429" in error_str or 
                "rate limit" in error_str or 
                "too many requests" in error_str or
                "ratelimit" in error_str
            )
            
            # Check for connection/timeout errors
            is_timeout = (
                "timeout" in error_str or
                "timed out" in error_str or
                "ConnectTimeout" in error_type or
                "APITimeoutError" in error_type or
                "TimeoutError" in error_type
            )
            
            # Retry for rate limits or timeouts
            if (is_rate_limit or is_timeout) and attempt < max_retries:
                wait_time = retry_delay * (attempt + 1)  # Exponential backoff: 5s, 10s, 15s
                error_type_name = "rate limit" if is_rate_limit else "timeout/connection"
                logger.warning(f"{error_type_name} error (attempt {attempt + 1}/{max_retries + 1}), waiting {wait_time} seconds before retry")
                time.sleep(wait_time)
            else:
                if is_rate_limit:
                    logger.error(f"Rate limit error after {max_retries + 1} attempts: {str(e)}")
                elif is_timeout:
                    logger.error(f"Connection/timeout error after {max_retries + 1} attempts: {str(e)}")
                    logger.error("This may indicate network connectivity issues or Azure OpenAI endpoint problems. Check your network connection and Azure OpenAI configuration.")
                else:
                    logger.error(f"LLM call failed: {str(e)}")
                raise


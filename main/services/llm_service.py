"""
LLM service for initializing Azure OpenAI Chat models.

TODO: Complete the implementation of initialize_llm() function.
This function should initialize an Azure OpenAI Chat model using LangChain's AzureChatOpenAI class.
"""

# TODO: Import necessary modules
# Verify these imports are correct for your implementation:
from typing import Dict, Any
from langchain_openai import AzureChatOpenAI
from ..config import logger


def initialize_llm(config: Dict[str, Any]) -> AzureChatOpenAI:
    """
    Initialize Azure ChatOpenAI LLM with GPT-4o-mini.
    
    This function creates and configures an Azure OpenAI Chat model instance
    that will be used for generating answers in the RAG pipeline.
    
    Args:
        config: Configuration dictionary containing Azure OpenAI settings.
                Expected keys:
                - 'azure_endpoint': Azure OpenAI endpoint URL
                - 'azure_llm_deployment': Deployment name (e.g., 'gpt-4o-mini')
                - 'azure_api_key': Azure OpenAI API key
                - 'api_version': API version (e.g., '2024-02-01')
        
    Returns:
        Initialized AzureChatOpenAI instance ready for use
        
    Raises:
        Exception: If LLM initialization fails
        
    Hints:
        1. Log the initialization start with the deployment name from config
        2. Wrap the initialization in a try-except block for error handling
        3. Create an AzureChatOpenAI instance with the following parameters:
           - azure_endpoint: from config['azure_endpoint']
           - azure_deployment: from config['azure_llm_deployment']
           - api_key: from config['azure_api_key']
           - api_version: from config['api_version']
           - temperature: 0.1 (low temperature for factual, consistent responses)
           - max_tokens: 1000 (maximum response length)
        4. Log the configuration details (temperature and max_tokens)
        5. Log successful initialization
        6. Return the initialized LLM instance
        7. In the except block, log the error with exc_info=True and re-raise it
    """
    # TODO: Step 1 - Log that you're starting LLM initialization
    # Use logger.info() with the deployment name from config
    
    try:
        # TODO: Step 2 - Create AzureChatOpenAI instance
        # Initialize the LLM with parameters from config dictionary
        # Remember to set:
        #   - azure_endpoint
        #   - azure_deployment  
        #   - api_key
        #   - api_version
        #   - temperature=0.1 (for factual accuracy)
        #   - max_tokens=1000
        
        # TODO: Step 3 - Log the configuration details
        # Use logger.debug() to log temperature and max_tokens settings
        
        # TODO: Step 4 - Log successful initialization
        # Use logger.info() to confirm the LLM was initialized successfully
        
        # TODO: Step 5 - Return the initialized LLM instance
        
        # Placeholder - remove this line once you implement the function
        raise NotImplementedError("TODO: Implement initialize_llm() function")
        
    except Exception as e:
        # TODO: Step 6 - Handle errors
        # Log the error with logger.error() including exc_info=True
        # Then re-raise the exception
        raise


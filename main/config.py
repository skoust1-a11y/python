"""
AutoMind Motors 

Centralized configuration and logging setup for the RAG ingestion pipeline.
"""

import os
import logging
import sys
from typing import Dict, Any
from dotenv import load_dotenv


def setup_logging(level: int = logging.INFO):
    """
    Configure logging for the application (console only)
    
    Args:
        level: Logging level (default: INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Override any existing configuration
    )
    
    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    logging.getLogger("watchfiles.main").setLevel(logging.WARNING)


# Initialize logging and create logger instance
setup_logging()
logger = logging.getLogger(__name__)


def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables"""
    logger = logging.getLogger(__name__)
    
    # TODO: Log that configuration loading is starting
    
    # TODO: Load environment variables from .env file using load_dotenv()
    
    # TODO: Get database configuration from environment variables
    # Get DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
    
    # TODO: Build database_url string in format: postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}
    
    # TODO: Get Azure OpenAI configuration from environment variables
    # Get AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION, COLLECTION_NAME
    
    # TODO: Build config dictionary with the following keys:
    # - database_url
    # - azure_endpoint
    # - azure_api_key
    # - azure_embedding_deployment
    # - api_version (with default value '2024-02-01')
    # - collection_name (with default value 'automind_embedding')
    
    config = {}
    
    # TODO: Validate required configuration variables
    # Check that azure_api_key, azure_endpoint, and azure_embedding_deployment are not None/empty
    # If any are missing, log an error and raise ValueError with appropriate message
    
    # TODO: Log successful configuration load with key details
    # Log embedding deployment, endpoint, database info, and collection name
    
    # TODO: Return the config dictionary
    return config
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
    logger.info('The Configuration Varibales has been started loading..')
    
    # TODO: Load environment variables from .env file using load_dotenv()
    try:
        load_dotenv()
        logger.info('Env Variables wil be loaded..')
    except Exception:
        logger.error('Error in loading env variables..')
        sys.exit(1)

    
    # TODO: Get database configuration from environment variables
    # Get DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
    try:
        user = os.getenv('DB_USER')
        password = os.getenv('DB_PASSWORD')
        host = os.getenv('DB_HOST')
        port = os.getenv('DB_PORT')
        db_name = os.getenv('DB_NAME')
        
        if not user:
            logger.error('DB_USER is empty')
            raise ValueError('DB_USER not found')
        if not password:
            logger.error('DB_PASSWORD is empty')
            raise ValueError('DB_PASSWORD not found')
        if not host:
            logger.error('DB_HOST is empty')
            raise ValueError('DB_HOST not found')
        if not port:
            logger.error('DB_PORT is empty')
            raise ValueError('DB_PORT not found')
        if not db_name:
            logger.error('DB_NAME is empty')
            raise ValueError('DB_NAME not found')
    except Exception:
        logger.error('Error loading DATABASE VARIABLES.')
        sys.exit(1)

    # TODO: Build database_url string in format: postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}

    CONNECTION_STRING = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"

    # database_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

    database_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"

    
    # TODO: Get Azure OpenAI configuration from environment variables
    # Get AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION, COLLECTION_NAME
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
    COLLECTION_NAME = os.getenv('COLLECTION_NAME','automind_embedding')

    
    # TODO: Build config dictionary with the following keys:
    # - database_url
    # - azure_endpoint
    # - azure_api_key
    # - azure_embedding_deployment
    # - api_version (with default value '2024-02-01')
    # - collection_name (with default value 'automind_embedding')
    
    config = {}

    config['database_url'] = database_url
    config['azure_endpoint'] = AZURE_OPENAI_ENDPOINT
    config['azure_api_key'] = AZURE_OPENAI_API_KEY
    config['azure_embedding_deployment'] = AZURE_OPENAI_DEPLOYMENT
    config['api_version'] = AZURE_OPENAI_API_VERSION
    config['collection_name'] = COLLECTION_NAME
    
    # TODO: Validate required configuration variables
    # Check that azure_api_key, azure_endpoint, and azure_embedding_deployment are not None/empty
    # If any are missing, log an error and raise ValueError with appropriate message

    missing_variables = [ key for key,value in config.items() if not value ]
    if missing_variables:
        error_msg = f"Missing required environment variables: {', '.join(missing_variables)}. Please check your .env file."
        logger.error(f"✗ {error_msg}")
        raise ValueError(error_msg)

    
    # TODO: Log successful configuration load with key details
    # Log embedding deployment, endpoint, database info, and collection name

    logger.info('Configuration Variables are correctly configured without missing')

    successful_configured_vars = [ key for key,value in config.items() if value ]
    if successful_configured_vars:
        success_msg = f"Successfully configured given required environment variables: {', '.join(successful_configured_vars)}."
        logger.info(f"✗ {success_msg}")

    logger.info(f'DB_USER is {user}')
    logger.info(f'DB_PASSWORD is {password}')
    logger.info(f'DB_HOST is {host}')
    logger.info(f'DB_PORT is {port}')
    logger.info(f'DB_NAME is {db_name}')
    
    
    # TODO: Return the config dictionary
    return config
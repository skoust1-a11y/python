"""
Configuration and logging setup for the RAG query pipeline.
"""

import os
import logging
import sys
from typing import Dict, Any
from dotenv import load_dotenv


def setup_logging(level: int = logging.INFO):
    """
    Configure application logging to stdout.
    
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


# Initialize logging and create module logger
setup_logging()
logger = logging.getLogger(__name__)


def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    logger.debug("Loading configuration from environment variables")
    load_dotenv()
    logger.debug(".env loaded (if present)")

    # Build DATABASE_URL from separate variables
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    
    # Validate database connection parameters
    if not all([db_user, db_password, db_host, db_port, db_name]):
        missing = [k for k, v in {
            'DB_USER': db_user,
            'DB_PASSWORD': db_password,
            'DB_HOST': db_host,
            'DB_PORT': db_port,
            'DB_NAME': db_name
        }.items() if not v]
        logger.error(f"Missing required database configuration: {', '.join(missing)}")
        raise ValueError(f"Missing required database configuration: {', '.join(missing)}")
    
    database_url = f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    config = {
        'database_url': database_url,
        'azure_endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
        'azure_api_key': os.getenv('AZURE_OPENAI_API_KEY'),
        'azure_embedding_deployment': os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT'),
        'azure_llm_deployment': os.getenv('AZURE_OPENAI_LLM_DEPLOYMENT'),
        'api_version': os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01'),
        'collection_name': os.getenv('COLLECTION_NAME', 'smart_auto_advisor'),
        'top_k': int(os.getenv('TOP_K', '5')),
        'chunk_size': int(os.getenv('CHUNK_SIZE', '1000')),
        'chunk_overlap': int(os.getenv('CHUNK_OVERLAP', '200')),
        'cors_origins': os.getenv('CORS_ORIGINS', '*').split(',') if os.getenv('CORS_ORIGINS') else ['*']
    }
    
    # Validate required configs (do not log secrets)
    if not config['azure_api_key']:
        logger.error("Missing AZURE_OPENAI_API_KEY")
        raise ValueError("AZURE_OPENAI_API_KEY not found in environment variables")
    if not config['azure_endpoint']:
        logger.error("Missing AZURE_OPENAI_ENDPOINT")
        raise ValueError("AZURE_OPENAI_ENDPOINT not found in environment variables")
    if not config['azure_llm_deployment']:
        logger.error("Missing AZURE_OPENAI_LLM_DEPLOYMENT")
        raise ValueError("AZURE_OPENAI_LLM_DEPLOYMENT not found in environment variables")
    if not config['azure_embedding_deployment']:
        logger.error("Missing AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        raise ValueError("AZURE_OPENAI_EMBEDDING_DEPLOYMENT not found in environment variables")
    
    # Validate numeric configs
    if config['top_k'] < 1 or config['top_k'] > 50:
        logger.warning(f"top_k={config['top_k']} is outside recommended range (1-50), using default")
        config['top_k'] = 5
    if config['chunk_size'] < 100:
        logger.warning(f"chunk_size={config['chunk_size']} is too small, using minimum 100")
        config['chunk_size'] = 100
    
    logger.info("Configuration loaded")
    logger.debug(f"Embedding deployment: {config['azure_embedding_deployment']}")
    logger.debug(f"LLM deployment: {config['azure_llm_deployment']}")
    logger.debug(f"Endpoint: {config['azure_endpoint']}")
    logger.debug(f"Collection: {config['collection_name']}")
    logger.debug(f"Top-K: {config['top_k']}")
    logger.debug(f"Chunking: size={config['chunk_size']}, overlap={config['chunk_overlap']}")
    
    return config



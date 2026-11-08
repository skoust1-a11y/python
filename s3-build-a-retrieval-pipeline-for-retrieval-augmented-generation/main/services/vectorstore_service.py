"""
Vectorstore service for initializing Azure OpenAI embeddings and PGVector connection.

TODO: Complete the implementation of initialize_embeddings() and setup_vectorstore() functions.
These functions handle embedding model initialization and vectorstore connection setup.
"""

# TODO: Import necessary modules
# Verify these imports are correct for your implementation:
from typing import Dict, Any
from langchain_openai import AzureOpenAIEmbeddings
from langchain_postgres import PGVector
from ..config import logger


def initialize_embeddings(config: Dict[str, Any]) -> AzureOpenAIEmbeddings:
    """
    Initialize Azure OpenAI embedding model.
    
    This function creates an Azure OpenAI embeddings instance that will be used
    to generate vector embeddings for text queries. It also tests the embedding
    generation to verify the model is working correctly.
    
    Args:
        config: Configuration dictionary containing Azure OpenAI settings.
                Expected keys:
                - 'azure_endpoint': Azure OpenAI endpoint URL
                - 'azure_embedding_deployment': Deployment name (e.g., 'text-embedding-3-small')
                - 'azure_api_key': Azure OpenAI API key
                - 'api_version': API version (e.g., '2024-02-01')
        
    Returns:
        Initialized AzureOpenAIEmbeddings instance ready for use
        
    Raises:
        Exception: If embedding model initialization fails
        
    Hints:
        1. Wrap the initialization in a try-except block for error handling
        2. Create an AzureOpenAIEmbeddings instance with parameters from config:
           - azure_endpoint: from config['azure_endpoint']
           - azure_deployment: from config['azure_embedding_deployment']
           - api_key: from config['azure_api_key']
           - api_version: from config['api_version']
        3. Test embedding generation by calling embed_query() with a test string
        4. Return the embeddings instance
        5. In the except block, re-raise the exception
    """
    try:
        # TODO: Step 1 - Create AzureOpenAIEmbeddings instance
        # Initialize with parameters from config dictionary:
        #   - azure_endpoint
        #   - azure_deployment
        #   - api_key
        #   - api_version
        embedding_model = AzureOpenAIEmbeddings(
            api_version=config.get('api_version'),
            azure_deployment=config.get('azure_embedding_deployment'),
            azure_endpoint=config.get('azure_endpoint'),
            api_key=config.get('azure_api_key')
        )
        
        # TODO: Step 2 - Test embedding generation
        # Call embed_query() with a test string (e.g., "test")
        embed = embedding_model.embed_query("test")
        logger.info(f'The Embedding query is : {embed}')
        # Store the result in a variable
        
        # TODO: Step 3 - Return the embeddings instance
        return embedding_model
        
        # Placeholder - remove this line once you implement the function
        
    except Exception as e:
        # TODO: Step 4 - Handle errors
        # Re-raise the exception
        logger.error(f'The error with intiialzing embedding model is : {e}')
        raise


def setup_vectorstore(config: Dict[str, Any], embeddings: AzureOpenAIEmbeddings) -> PGVector:
    """
    Initialize PGVector vectorstore connected to existing embeddings.
    
    This function creates a PGVector instance that connects to the PostgreSQL
    database and uses the provided embeddings model. The vectorstore will be
    used to retrieve similar document chunks based on semantic similarity.
    
    Args:
        config: Configuration dictionary containing database settings.
                Expected keys:
                - 'database_url': PostgreSQL connection string
                - 'collection_name': Name of the collection/table in the database
        embeddings: Initialized AzureOpenAIEmbeddings instance
        
    Returns:
        Initialized PGVector instance ready for similarity search
        
    Raises:
        Exception: If vectorstore setup fails
        
    Hints:
        1. Wrap the setup in a try-except block for error handling
        2. Create a PGVector instance with:
           - connection: from config['database_url']
           - embeddings: the embeddings parameter
           - collection_name: from config['collection_name']
           - use_jsonb: True (for storing metadata as JSONB)
        3. Return the vectorstore instance
        4. In the except block, re-raise the exception
    """
    try:
        # TODO: Step 1 - Create PGVector instance
        # Initialize with:
        #   - connection: from config['database_url']
        #   - embeddings: the embeddings parameter
        #   - collection_name: from config['collection_name']
        #   - use_jsonb: True
        pg_vector = PGVector(
            collection_name=config.get('collection_name'),
            connection=config.get('database_url'),
            use_jsonb=True,
            embeddings=embeddings
        )
        
        # TODO: Step 2 - Return the vectorstore instance

        return pg_vector
        
        # Placeholder - remove this line once you implement the function
        
    except Exception as e:
        # TODO: Step 3 - Handle errors
        # Re-raise the exception
        logger.error(f'The error is: {e}')
        raise


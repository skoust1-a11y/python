"""
RAG Service Module
Provides shared services for API and CLI usage.

This module:
- Initializes Azure OpenAI configuration
- Manages vector index and query engine instances
- Provides singleton access to RAG components
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from llama_index.core import Settings, VectorStoreIndex, StorageContext
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.vector_stores.postgres import PGVectorStore
from main.service.query_engine import create_query_engine as create_qe
from main.service.semantic_chunking import create_semantic_splitter, generate_nodes_from_documents

logger = logging.getLogger(__name__)

# Global instances
_index: Optional[VectorStoreIndex] = None
_llm = None
_embed_model = None


def initialize_services():
    """Initialize all services (LLM, embeddings, index)."""
    global _index, _llm, _embed_model
    
    if _index is not None:
        logger.info("Services already initialized, reusing existing instances")
        return
    
    load_dotenv()
    
    # Validate required environment variables
    required_vars = [
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_API_KEY',
        'AZURE_OPENAI_LLM_DEPLOYMENT',
        'AZURE_OPENAI_EMBEDDING_DEPLOYMENT',
        'DB_USER',
        'DB_PASSWORD',
        'DB_HOST',
        'DB_PORT',
        'DB_NAME',
        'DB_TABLE_NAME'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info("✓ Environment variables validated")
    
    # Configure Azure OpenAI
    logger.info("Initializing Azure OpenAI services...")
    
    try:
        # Get environment variables with validation
        llm_deployment = os.getenv('AZURE_OPENAI_LLM_DEPLOYMENT')
        llm_api_key = os.getenv('AZURE_OPENAI_API_KEY')
        llm_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        
        if not all([llm_deployment, llm_api_key, llm_endpoint]):
            raise ValueError("Missing required Azure OpenAI LLM configuration")
        
        # TODO: Initialize Azure OpenAI LLM
        # HINT: Create an AzureOpenAI instance and assign it to _llm
        # HINT: Required parameters:
        #   - model: Get from 'AZURE_OPENAI_LLM_MODEL' env var (default: 'gpt-4o-mini')
        #   - deployment_name: Use llm_deployment variable
        #   - api_key: Use llm_api_key variable
        #   - azure_endpoint: Use llm_endpoint variable
        #   - api_version: Get from 'AZURE_OPENAI_API_VERSION' env var (default: '2024-02-15-preview')
        # Your code here:
        raise NotImplementedError("Azure OpenAI LLM initialization is not implemented yet. Please complete the implementation.")
        
        # TODO: Get embedding deployment name from environment variable
        # HINT: Use os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT')
        # Your code here:
        embed_deployment = None
        
        # TODO: Validate embedding configuration
        # HINT: Check if embed_deployment, llm_api_key, and llm_endpoint are all present
        # HINT: Raise ValueError if any are missing with message "Missing required Azure OpenAI Embedding configuration"
        # Your code here:
        
        # TODO: Initialize Azure OpenAI Embedding model
        # HINT: Create an AzureOpenAIEmbedding instance and assign it to _embed_model
        # HINT: Required parameters:
        #   - model: Get from 'AZURE_OPENAI_EMBEDDING_MODEL' env var (default: 'text-embedding-3-small')
        #   - deployment_name: Use embed_deployment variable
        #   - api_key: Use llm_api_key variable
        #   - azure_endpoint: Use llm_endpoint variable
        #   - api_version: Get from 'AZURE_OPENAI_API_VERSION' env var (default: '2024-02-15-preview')
        # Your code here:
        raise NotImplementedError("Azure OpenAI Embedding initialization is not implemented yet. Please complete the implementation.")
        
        # Verify objects were created successfully
        if _llm is None:
            raise ValueError("Failed to create LLM instance - AzureOpenAI returned None")
        if _embed_model is None:
            raise ValueError("Failed to create Embedding instance - AzureOpenAIEmbedding returned None")
        
        logger.debug(f"Created LLM instance: {type(_llm).__name__}")
        logger.debug(f"Created Embedding instance: {type(_embed_model).__name__}")
        
        # TODO: Assign LLM and Embedding models to LlamaIndex Settings
        # HINT: Use Settings.llm and Settings.embed_model to assign the models globally
        # HINT: Wrap in try-except to handle any potential errors gracefully
        # HINT: If assignment fails, it's non-critical - log a warning and continue
        # Your code here:
        
        logger.info(f"✓ LLM configured: {os.getenv('AZURE_OPENAI_LLM_MODEL', 'gpt-4o-mini')}")
        logger.info(f"✓ Embedding model configured: {os.getenv('AZURE_OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')}")
        
    except ValueError as ve:
        logger.error(f"Configuration error: {ve}")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize Azure OpenAI services: {e}", exc_info=True)
        raise ValueError(f"Azure OpenAI initialization failed: {e}") from e
    
    # Load or create index
    _index = load_or_create_index(_embed_model)
    
    logger.info("✓ All services initialized successfully")


def load_or_create_index(embed_model) -> VectorStoreIndex:
    """Load existing index from PostgreSQL or create a new one."""
    logger.info("Loading or creating vector index...")
    
    # TODO: Initialize PGVector store
    # HINT: Use PGVectorStore.from_params() to create the vector store
    # HINT: Required parameters from environment variables:
    #   - database: DB_NAME
    #   - host: DB_HOST
    #   - password: DB_PASSWORD
    #   - port: DB_PORT
    #   - user: DB_USER
    #   - table_name: DB_TABLE_NAME
    #   - embed_dim: 1536 (dimension for text-embedding-3-small)
    # Your code here:
    vector_store = None  # Replace with actual implementation
    
    # TODO: Create StorageContext from the vector store
    # HINT: Use StorageContext.from_defaults() and pass the vector_store
    # Your code here:
    storage_context = None  # Replace with actual implementation
    
    # TODO: Try to load existing index from PostgreSQL, or create a new empty one
    # HINT: Use try-except block
    # HINT: In try block: Use VectorStoreIndex.from_vector_store() with vector_store and embed_model
    # HINT: In except block: Create new VectorStoreIndex with empty nodes=[], storage_context, and embed_model
    # Your code here:
    raise NotImplementedError("load_or_create_index method is not implemented yet. Please complete the implementation.")


def get_index() -> VectorStoreIndex:
    """Get the vector index instance."""
    if _index is None:
        initialize_services()
    return _index


def get_query_engine(similarity_top_k: int = 2, filters=None):
    """
    Get a fresh query engine instance with specified similarity_top_k.
    
    Always creates a new query engine to ensure it uses the most up-to-date index.
    
    Args:
        similarity_top_k: Number of top similar nodes to retrieve
        filters: Optional MetadataFilters object for diet-specific filtering
        
    Returns:
        QueryEngine instance (freshly created)
    """
    if _index is None:
        initialize_services()
    
    # Always create fresh query engine - no caching
    return create_qe(_index, _llm, similarity_top_k=similarity_top_k, filters=filters)


def get_embed_model():
    """Get the embedding model instance."""
    if _embed_model is None:
        initialize_services()
    return _embed_model


def get_llm():
    """Get the LLM instance."""
    if _llm is None:
        initialize_services()
    return _llm


def add_documents_to_index(documents, use_semantic_splitter=True):
    """
    Add new documents to the existing index.
    
    Args:
        documents: List of Document objects to add
        use_semantic_splitter: Whether to use semantic chunking (default: True)
        
    Returns:
        dict: Result message with number of documents indexed
    """
    global _index
    
    if _index is None:
        initialize_services()
    
    logger.info(f"Adding {len(documents)} document(s) to index...")
    logger.info(f"  Using semantic chunking: {use_semantic_splitter}")
    
    # TODO: Implement document indexing with optional semantic chunking
    # HINT: Check if use_semantic_splitter is True
    # HINT: If True:
    #   1. Get embedding model using get_embed_model()
    #   2. Create semantic splitter using create_semantic_splitter(embed_model)
    #   3. Generate nodes using generate_nodes_from_documents(semantic_splitter, documents)
    #   4. Insert each node into the index using _index.insert(node)
    # HINT: If False:
    #   1. Insert each document directly using _index.insert(doc)
    # HINT: Use try-except to handle insertion errors
    # HINT: Return a dictionary with success message
    # Your code here:
    raise NotImplementedError("add_documents_to_index method is not implemented yet. Please complete the implementation.")


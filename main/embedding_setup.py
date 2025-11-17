"""
RAG infrastructure setup: PostgreSQL/PgVector checks, Azure OpenAI embeddings,
PGVector store initialization, sample CRUD operations, and similarity search.
"""

import sys
import logging
import psycopg2
from pathlib import Path

# Add project root to Python path to allow imports when running script directly
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from main.sample_data import SAMPLE_DOCUMENTS
from main.config import setup_logging, load_config
from main.services.vectorstore_service import VectorstoreService

logger = logging.getLogger(__name__)

# --------------------------
# Utilities
# --------------------------

def normalize_db_url(database_url: str) -> str:
    """Convert SQLAlchemy-style DB URL to psycopg2 compatible URL."""
    return (
        database_url.replace("postgresql+psycopg2://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
    )


# --------------------------
# Step 1: Database and PgVector check
# --------------------------

def check_database_connection(database_url: str):
    """Test DB connection and ensure PgVector extension exists."""
    logger.info("=" * 80)
    logger.info("TESTING DATABASE CONNECTION")
    logger.info("=" * 80)

    try:
        conn = psycopg2.connect(normalize_db_url(database_url))
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                logger.info(f"PostgreSQL version: {cursor.fetchone()[0].split(',')[0]}")

                cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
                if cursor.fetchone():
                    logger.info("PgVector extension already enabled ✅")
                else:
                    logger.warning("PgVector not found, enabling...")
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    logger.info("PgVector extension enabled successfully ✅")

        return True
    except Exception as e:
        logger.error(f"Database test failed ❌: {e}")
        return False


# --------------------------
# Step 2-3: Initialize vectorstore service
# --------------------------

def initialize_vectorstore_service():
    """Initialize the vectorstore service."""
    logger.info("=" * 80)
    logger.info("INITIALIZING VECTORSTORE SERVICE")
    logger.info("=" * 80)
    
    try:
        # TODO: Create an instance of VectorstoreService
        
        # TODO: Return the service instance
        pass
    except Exception as e:
        # TODO: Add exception handling here
        # Log error appropriately
        # Re-raise the exception
        pass


# --------------------------
# Step 4: CRUD — create
# --------------------------

def insert_sample_documents(service, documents):
    """
    Insert pre-created LangChain Document objects into the vectorstore.
    
    Args:
        service: The VectorstoreService instance
        documents: List of Document objects to insert
        
    Returns:
        List of inserted document IDs
    """
    logger.info("=" * 80)
    logger.info("INSERTING SAMPLE DOCUMENTS")
    logger.info("=" * 80)

    # TODO: Check if documents list is empty
    # If empty, log a warning and return empty list

    try:
        # TODO: Call service.add_documents() method with the documents list
        
        # TODO: Get the list of document IDs from the result
        
        # TODO: Log success message with number of documents inserted
        
        # TODO: Log each document with its ID and document name from metadata
        
        # TODO: Return the list of document IDs
        pass
    except Exception as e:
        # TODO: Add exception handling here
        # Log error appropriately
        # Return empty list on failure
        pass


# --------------------------
# Step 5: Similarity search
# --------------------------

def perform_similarity_search(service, query_text, top_k=3, return_result=False):
    """
    Perform similarity search with scores for detailed logging.
    Can optionally return the best result.
    
    Args:
        service: The VectorstoreService instance
        query_text: The search query
        top_k: Number of results to return
        return_result: If True, returns the best result as a dict. If False, only logs results.
        
    Returns:
        dict or None: If return_result=True, returns the best matching document with content and metadata.
                     Otherwise returns None (only logs results).
    """
    logger.info("=" * 80)
    logger.info(f"SIMILARITY SEARCH FOR: {query_text}")
    logger.info("=" * 80)

    try:
        # TODO: Perform similarity search with scores using service.vectorstore.similarity_search_with_score()
        # Pass query_text and top_k (k parameter)
        
        # TODO: Check if results are empty
        # If empty, log a warning and return None
        
        # TODO: Iterate through results and log each result
        # For each result, calculate similarity score (1 / (1 + distance))
        # Log rank, distance, similarity, content, and metadata
        
        # TODO: If return_result is True and results exist, return the best result
        # Extract the best document (first result) and return as dict with "content" and "metadata" keys
        # Log that you're returning the best result
        
        # TODO: Return None if return_result is False
        pass

    except Exception as e:
        # TODO: Add exception handling here
        # Log error appropriately
        # Return None on failure
        pass


# --------------------------
# Main execution flow
# --------------------------

def main():
    setup_logging()
    config = load_config()

    if not check_database_connection(config["database_url"]):
        return

    # Initialize vectorstore service (handles embeddings and vectorstore initialization)
    service = initialize_vectorstore_service()

    # Insert pre-created LangChain Document objects related to Smart Auto Advisor
    insert_sample_documents(service, SAMPLE_DOCUMENTS)
    
    # Test similarity search
    perform_similarity_search(service, "What are the features and pricing of the EcoSport Hybrid?")


if __name__ == "__main__":
    main()

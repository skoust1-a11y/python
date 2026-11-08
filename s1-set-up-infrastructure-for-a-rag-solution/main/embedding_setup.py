"""
RAG infrastructure setup: PostgreSQL/PgVector checks, Azure OpenAI embeddings,
PGVector store initialization, sample CRUD operations, and similarity search.
"""

import sys
import logging
import psycopg2
from pathlib import Path
from main.services.vectorstore_service import get_vectorstore_service

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
        vector_service = VectorstoreService()
        # TODO: Return the service instance
        return vector_service
    except Exception as e:
        # TODO: Add exception handling here
        # Log error appropriately
        logger.error('vector service not initialized at embedding_setup')
        # Re-raise the exception
        raise Exception('vector service not initialized at embedding_setup')


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
    if len(documents) == 0:
        logger.info('Empty List of Documents')
        return []

    try:
        # TODO: Call service.add_documents() method with the documents list
        list_of_ids = service.add_documents(documents)
        
        # TODO: Get the list of document IDs from the result
        
        # TODO: Log success message with number of documents inserted
        logger.info(f'{len(list_of_ids)} of Documents are inserted successfully..')
        
        # TODO: Log each document with its ID and document name from metadata
        for log_doc in documents:
            logger.info(f'Documents added with {log_doc.metadata['id']} and {log_doc.metadata['name']} has been inserted successfully.')
        # TODO: Return the list of document IDs
        return list_of_ids
    except Exception as e:
        # TODO: Add exception handling here
        # Log error appropriately
        logger.error('The Documents have been not added.')
        # Return empty list on failure
        return []


# --------------------------
# Step 5: Similarity search
# --------------------------

def perform_similarity_search(service : VectorstoreService, query_text, top_k=3, return_result=False):
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
        results = service.vectorstore.similarity_search_with_score(query=query_text,k=top_k)

        
        # TODO: Check if results are empty
        # If empty, log a warning and return None
        if len(results) == 0:
            logger.warning('The Extracted search results are empty')
            return None
        
        # TODO: Iterate through results and log each result
        # For each result, calculate similarity score (1 / (1 + distance))
        # Log rank, distance, similarity, content, and metadata
        c = 0
        for doc,distance in results:
            similarity_score = (1 / (1 + distance))
            logger.info(
                f"Rank: {c}, "
                f"Distance: {distance:.4f}, "
                f"Similarity: {similarity_score:.4f}"
                f"content: {doc.page_content}"
                f"metadata : {doc.metadata}"
            )
            c += 1


            
        best_doc,best_score = results[0]

        # TODO: If return_result is True and results exist, return the best result
        # Extract the best document (first result) and return as dict with "content" and "metadata" keys
        # Log that you're returning the best result
        if return_result and len(results) > 0:
            logger.info(f'Returned the best Result search')
            return {
                'content' : best_doc.page_content,
                'metadata' : best_doc.metadata
            }
        else:
            return None
        # TODO: Return None if return_result is False
    except Exception as e:
        # TODO: Add exception handling here
        # Log error appropriately
        logger.error(f'The Similar Results are not able to fetch. {e}')
        # Return None on failure
        return None


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

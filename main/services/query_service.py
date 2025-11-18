"""
Vector similarity search service.
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_postgres import PGVector

from main.config import logger
from main.services.embedding_service import EmbeddingService


class QueryService:
    """Service for querying the vector database."""
    
    def __init__(self, collection_name: Optional[str] = None):
        """
        Initialize the query service.
        
        Args:
            collection_name: Name of the collection in vector database (default from config)
        """
        self.logger = logger or logging.getLogger(__name__)
        self.embedding_service = EmbeddingService(collection_name=collection_name)
        self.vectorstore: Optional[PGVector] = None
    
    def _get_vectorstore(self) -> PGVector:
        """Get or initialize the vectorstore."""
        # TODO: Implement vectorstore retrieval/initialization.
        # Expected:
        # - If `self.vectorstore` is already set, return it
        # - Otherwise, call `self.embedding_service.get_vectorstore()` and cache it
        # - Return the PGVector instance
        raise NotImplementedError(
            "_get_vectorstore() not implemented. Retrieve and cache PGVector via EmbeddingService."
        )
    
    def similarity_search(
        self, 
        query: str, 
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search on the vector database.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            filter: Optional metadata filter
            
        Returns:
            List of result dictionaries with content and metadata
        """
        # TODO: Implement similarity search with scores.
        # Expected steps:
        # 1) Get vectorstore via `_get_vectorstore()`
        # 2) Call `similarity_search_with_score(query, k=top_k, filter=filter?)`
        # 3) Format each (Document, score) into:
        #    {"content": doc.page_content, "metadata": doc.metadata, "score": float(score), "distance": float(score)}
        # 4) Return the formatted list
        # 5) Include basic logging and error handling
        raise NotImplementedError(
            "similarity_search() not implemented. Use similarity_search_with_score and format results."
        )
    
    def similarity_search_simple(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform similarity search without scores (simpler interface).
        
        Args:
            query: Search query text
            top_k: Number of results to return
            
        Returns:
            List of result dictionaries with content and metadata
        """
        # TODO: Implement simple similarity search (no scores).
        # Expected:
        # - Get vectorstore via `_get_vectorstore()`
        # - Call `similarity_search(query, k=top_k)`
        # - Return list of {"content": doc.page_content, "metadata": doc.metadata}
        # - Include basic logging and error handling
        raise NotImplementedError(
            "similarity_search_simple() not implemented. Use similarity_search and format results."
        )


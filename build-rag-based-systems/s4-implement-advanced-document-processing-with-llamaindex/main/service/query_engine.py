"""
Query Engine Module
Handles query engine creation from vector index.

This module provides:
- Query engine creation from vector index with configurable similarity search
- Support for metadata filtering for targeted diet information retrieval
"""

import logging
from llama_index.core import VectorStoreIndex

logger = logging.getLogger(__name__)


def create_query_engine(index : VectorStoreIndex, llm, similarity_top_k=2, filters=None):
    """
    Create Query Engine from index.
    
    Args:
        index: VectorStoreIndex
        llm: Azure OpenAI LLM
        similarity_top_k: Number of top similar nodes to retrieve (default: 2)
        filters: Optional MetadataFilters object for diet-specific filtering
        
    Returns:
        QueryEngine: The created query engine
    """
    logger.info("Creating query engine...")
    
    # TODO: Create query engine from the index and return it
    # HINT: Use the index's as_query_engine() method
    # HINT: Pass the following parameters:
    #   - llm: The language model for generating responses
    #   - similarity_top_k: Number of similar nodes to retrieve
    #   - filters: Optional metadata filters for targeted retrieval
    # Your code here:
    if filters is not None:
        query_engine = index.as_query_engine(llm=llm,similarity_top_k=similarity_top_k,filters=filters)
    else:
        query_engine = index.as_query_engine(llm=llm,similarity_top_k=similarity_top_k)
        
    return query_engine 


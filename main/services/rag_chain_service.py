"""
RAG chain service for building and managing LCEL chains.

TODO: Complete the implementation of format_docs() and build_rag_chain() functions.
These functions handle document formatting and LCEL chain construction for the RAG pipeline.
"""

# TODO: Import necessary modules
# Verify these imports are correct for your implementation:
from typing import List, Dict, Any
from langchain_postgres import PGVector
from langchain_openai import AzureChatOpenAI
from langchain_core.documents import Document
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from ..config import logger
from ..prompts import create_production_prompt


def format_docs(docs: List[Document]) -> str:
    """
    Format retrieved documents for context with source attribution.
    
    This function takes a list of Document objects and formats them into a single
    string with source citations, making it suitable for inclusion in LLM prompts.
    
    Args:
        docs: List of retrieved Document objects with metadata
        
    Returns:
        Formatted string with source citations, separated by delimiters.
        Format: "[Source N: filename | Chunk ID: id]\ncontent\n\n---\n\n"
        Returns "No relevant context found." if docs list is empty.
        
    Hints:
        1. Log the number of documents being formatted
        2. Check if docs list is empty - if so, log warning and return early
        3. Initialize an empty list for formatted chunks
        4. Iterate through documents with enumerate (starting at 1)
        5. Extract source from doc.metadata.get('source', 'Unknown')
        6. Extract chunk_id from doc.metadata.get('chunk_id', 'N/A')
        7. Get content from doc.page_content
        8. Log each chunk being formatted
        9. Format each chunk as: "[Source N: source | Chunk ID: chunk_id]\ncontent"
        10. Append formatted chunk to list
        11. Join all chunks with "\n\n---\n\n" separator
        12. Log successful formatting
        13. Return the formatted string
    """
    # TODO: Step 1 - Log the number of documents being formatted
    
    # TODO: Step 2 - Check if docs list is empty
    # If empty, log a warning and return "No relevant context found."
    
    # TODO: Step 3 - Initialize list for formatted chunks
    
    # TODO: Step 4 - Iterate through documents
    # Use enumerate starting at 1 to get index numbers
    
    # TODO: Step 5 - Extract metadata from each document
    # Get source from doc.metadata.get('source', 'Unknown')
    # Get chunk_id from doc.metadata.get('chunk_id', 'N/A')
    # Get content from doc.page_content
    
    # TODO: Step 6 - Log each chunk being formatted
    
    # TODO: Step 7 - Format each chunk
    # Format: "[Source N: source | Chunk ID: chunk_id]\ncontent"
    # Append to formatted_chunks list
    
    # TODO: Step 8 - Join all formatted chunks
    # Use "\n\n---\n\n" as separator
    
    # TODO: Step 9 - Log successful formatting
    
    # TODO: Step 10 - Return the formatted string
    
    # Placeholder - remove this line once you implement the function
    raise NotImplementedError("TODO: Implement format_docs() function")


def build_rag_chain(
    vectorstore: PGVector, 
    llm: AzureChatOpenAI, 
    config: Dict[str, Any]
) -> tuple:
    """
    Build complete LCEL chain: retriever → prompt → LLM → parser.
    
    This function constructs a LangChain Expression Language (LCEL) chain that:
    1. Retrieves relevant documents from the vectorstore
    2. Formats them with source citations
    3. Passes them to the prompt template along with the question
    4. Generates an answer using the LLM
    5. Parses the output to a string
    
    Args:
        vectorstore: PGVector instance connected to the vector database
        llm: AzureChatOpenAI instance for answer generation
        config: Configuration dictionary containing 'top_k' for retrieval
        
    Returns:
        Tuple of (rag_chain, retriever) where:
        - rag_chain: The complete LCEL chain ready for invocation
        - retriever: The retriever instance for direct document retrieval
        
    Hints:
        1. Log that you're building the RAG chain
        2. Create retriever from vectorstore using as_retriever()
           - search_type: "similarity"
           - search_kwargs: {"k": config['top_k']}
        3. Log retriever creation with top_k value
        4. Create prompt template using create_production_prompt()
        5. Log prompt template creation
        6. Build LCEL chain using pipe operator (|):
           - Start with a dictionary containing:
             * "context": retriever | format_docs (retrieves and formats docs)
             * "question": RunnablePassthrough() (passes question through)
           - Pipe to prompt template
           - Pipe to llm
           - Pipe to StrOutputParser()
        7. Log successful chain creation
        8. Return tuple of (rag_chain, retriever)
    """
    # TODO: Step 1 - Log that you're building the RAG chain
    
    # TODO: Step 2 - Create retriever from vectorstore
    # Use as_retriever() with:
    #   - search_type="similarity"
    #   - search_kwargs={"k": config['top_k']}
    # Log the top_k value being used
    
    # TODO: Step 3 - Log retriever creation
    
    # TODO: Step 4 - Create prompt template
    # Call create_production_prompt() function
    # Log prompt template creation
    
    # TODO: Step 5 - Build LCEL chain
    # Use pipe operator (|) to chain components:
    #   - Start with dictionary: {"context": retriever | format_docs, "question": RunnablePassthrough()}
    #   - Pipe to prompt
    #   - Pipe to llm
    #   - Pipe to StrOutputParser()
    # Store in rag_chain variable
    
    # TODO: Step 6 - Log successful chain creation
    # Include the chain flow: retriever -> prompt -> LLM -> parser
    
    # TODO: Step 7 - Return tuple of (rag_chain, retriever)
    
    # Placeholder - remove this line once you implement the function
    raise NotImplementedError("TODO: Implement build_rag_chain() function")


"""
Document chunking service.
"""

import logging
from datetime import datetime
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from main.config import logger, load_config


class ChunkingService:
    """Service for chunking documents into smaller pieces."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        """
        Initialize the chunking service.
        
        Args:
            chunk_size: Size of each chunk (default from config)
            chunk_overlap: Overlap between chunks (default from config)
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # TODO: Initialize chunking configuration and text splitter.
        # Expected steps:
        # 1) If `chunk_size` or `chunk_overlap` is None, load defaults from `load_config()`
        # 2) Assign `self.chunk_size` and `self.chunk_overlap`
        # 3) Create `self.text_splitter = RecursiveCharacterTextSplitter(...)`
        #    with sensible separators and `length_function=len`
        # Note: Keep this constructor side-effect free except initialization.
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = None  # to be set by students
        
        self.logger.debug(f"ChunkingService initialized: chunk_size={chunk_size}, overlap={chunk_overlap}")
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks with overlap.
        
        Args:
            documents: List of Document objects to chunk
            
        Returns:
            List of chunked Document objects
        """
        # TODO: Implement document chunking.
        # Expected steps:
        # 1) Log the number of documents to chunk
        # 2) Use `self.text_splitter.split_documents(documents)` to create chunks
        # 3) For each chunk, add metadata such as:
        #    - "chunk_id" (sequential index)
        #    - "chunk_identifier" (derive from source_file/source_url + page + chunk_id)
        #    - "chunk_size" (len of chunk.page_content)
        #    - "upload_time" (ISO 8601 string)
        # 4) Return the list of chunked `Document` objects
        raise NotImplementedError(
            "chunk_documents() not implemented. Split documents with text_splitter and attach chunk metadata."
        )
    
    def chunk_text(self, text: str, metadata: dict = None) -> List[Document]:
        """
        Chunk a single text string into Document objects.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks
            
        Returns:
            List of chunked Document objects
        """
        # TODO: Implement convenience chunking for raw text.
        # Expected:
        # - Wrap `text` into a `Document(page_content=text, metadata=metadata or {})`
        # - Delegate to `self.chunk_documents([doc])`
        # - Return the result
        raise NotImplementedError(
            "chunk_text() not implemented. Wrap text in Document and delegate to chunk_documents."
        )


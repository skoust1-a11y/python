"""
Document chunking service.
"""

import logging
from datetime import datetime,timezone
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from main.config import logger, load_config


config = load_config()

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
        self.chunk_size = chunk_size or config.get('chunk_size')
        self.chunk_overlap = chunk_overlap or config.get('chunk_overlap')
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = self.chunk_size,
            chunk_overlap =self.chunk_overlap, 
            separators=["\n\n", "\n", " ", ""],
            length_function=len  
        )  # to be set by students
        
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
        self.logger.info(f'The the number of documents to chunk: {len(documents)}')
        # 2) Use `self.text_splitter.split_documents(documents)` to create chunks
        try:
            chunks : List[Document] = self.text_splitter.split_documents(documents)
            # 3) For each chunk, add metadata such as:
            #    - "chunk_id" (sequential index)
            #    - "chunk_identifier" (derive from source_file/source_url + page + chunk_id)
            #    - "chunk_size" (len of chunk.page_content)
            #    - "upload_time" (ISO 8601 string)
            # 4) Return the list of chunked `Document` objects
            for i,chunk in enumerate(chunks,start=1):

                source = chunk.metadata.get('source_file') or chunk.metadata.get('source_url', 'unknown')
                page   = chunk.metadata.get('page', 0)
                chunk.metadata['chunk_id'] = i

                chunk.metadata['chunk_identifier'] = f"{source}_page{page}_chunk{i}"
                chunk.metadata['chunk_size'] = len(chunk.page_content)
                chunk.metadata['upload_time'] = datetime.now(timezone.utc).isoformat()
            return chunks
        except Exception as e:
            raise Exception(f"The Error is: {e}")
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
        try:
            doc = Document(page_content=text,metadata=metadata or {})
            docs : List[Document] = self.chunk_documents([doc])
            return docs
        except Exception as e:
            raise Exception(f'chunk text exception raised: {e}')
        raise NotImplementedError(
            "chunk_text() not implemented. Wrap text in Document and delegate to chunk_documents."
        )


"""
Text file loading service.
"""

import os
import logging
from typing import List
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document

from main.config import logger


class TextLoaderService:
    """Service for loading text documents."""
    
    def __init__(self, encoding: str = 'utf-8'):
        """
        Initialize the text loader service.
        
        Args:
            encoding: File encoding (default: utf-8)
        """
        self.encoding = encoding
        self.logger = logger or logging.getLogger(__name__)
    
    def load(self, file_path: str) -> List[Document]:
        """
        Load a text file and return Document objects.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            List of Document objects
            
        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: If loading fails
        """
        # TODO: Implement text file loading.
        # Expected steps:
        # 1) Validate that `file_path` exists (raise FileNotFoundError if missing)
        # 2) Initialize `TextLoader(file_path, encoding=self.encoding)` and call `load()` to get List[Document]
        # 3) For each document, attach metadata:
        #    - "source_file" (os.path.basename(file_path))
        #    - "file_type" = "txt"
        # 4) Return the list of documents and add basic logging/error handling
        raise NotImplementedError(
            "load() not implemented. Use TextLoader with configured encoding, add metadata, and return documents."
        )



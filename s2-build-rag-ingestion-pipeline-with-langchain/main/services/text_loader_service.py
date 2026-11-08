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
        if not os.path.exists(file_path):
            self.logger.error('Text filePath does not exist')
            raise FileNotFoundError("Text File not Found.")
        # 2) Initialize `PyPDFLoader(file_path)` and call `loader.load()` to get List[Document]
        try:
            pdf_loader = TextLoader(file_path=file_path,encoding=self.encoding)

            all_docs : List[Document] = pdf_loader.load()
            self.logger.info(f"Eager loading Text {file_path}: FINISHED")

            updated_docs = []

            for doc in all_docs:
                self.logger.info(f"Entered the loop for iterating docs")
                doc.metadata['source_file'] = os.path.basename(file_path)
                doc.metadata['file_type'] = "txt"
                self.logger.info(f"Metadata Updated for DOC_OBJECT FOR A Text path: {file_path}.")
                updated_docs.append(doc)
            
            return updated_docs
        except Exception as e:
            logger.error(f"Error loading Text {file_path}: {e}")
            return []
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



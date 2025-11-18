"""
HTML file loading service.
"""

import os
import logging
from typing import List
from langchain_community.document_loaders import BSHTMLLoader
from langchain_core.documents import Document

from main.config import logger


class HTMLLoaderService:
    """Service for loading HTML documents."""
    
    def __init__(self):
        """Initialize the HTML loader service."""
        self.logger = logger or logging.getLogger(__name__)
    
    def load(self, file_path: str) -> List[Document]:
        """
        Load an HTML file and return Document objects.
        
        Args:
            file_path: Path to the HTML file
            
        Returns:
            List of Document objects
            
        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: If loading fails
        """
        # TODO: Implement HTML file loading.
        # Expected steps:
        # 1) Validate that `file_path` exists (raise FileNotFoundError if missing)
        # 2) Initialize `BSHTMLLoader(file_path, bs_kwargs={"features": "html.parser"})`
        # 3) Call `loader.load()` to get a List[Document]
        # 4) Attach metadata to each document: "source_file" (basename) and "file_type" = "html"
        # 5) Return the documents and add basic logging/error handling
        raise NotImplementedError(
            "load() not implemented. Use BSHTMLLoader(html.parser), add metadata, and return documents."
        )


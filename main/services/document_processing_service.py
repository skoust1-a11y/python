"""
Multi-source document processing service.
Handles file type detection and routes to appropriate loader.
"""

import os
import logging
from typing import List, Optional
from langchain_core.documents import Document

from main.config import logger
from main.services.pdf_loader_service import PDFLoaderService
from main.services.text_loader_service import TextLoaderService
from main.services.html_loader_service import HTMLLoaderService
from main.services.web_loader_service import WebLoaderService

def detect_file_type(file_path: str) -> Optional[str]:
    """
    Detect file type from file extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File type string ('pdf', 'txt', 'html', 'docx') or None if unsupported
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == ".pdf":
        return "pdf"
    elif file_extension == ".txt":
        return "txt"
    elif file_extension in [".html", ".htm"]:
        return "html"
    elif file_extension == ".docx":
        return "docx"
    else:
        return None

def is_supported_file(file_path: str) -> bool:
    """
    Check if file is supported based on extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if file is supported, False otherwise
    """
    file_type = detect_file_type(file_path)
    return file_type is not None


class DocumentProcessingService:
    """Service for processing documents from multiple sources."""
    
    def __init__(self):
        """Initialize the document processing service."""
        self.logger = logger or logging.getLogger(__name__)
        self.pdf_loader = PDFLoaderService()
        self.text_loader = TextLoaderService()
        self.html_loader = HTMLLoaderService()
        self.web_loader = WebLoaderService()
    
    def process_file(self, file_path: str) -> List[Document]:
        """
        Process a file and return Document objects.
        Automatically detects file type and uses appropriate loader.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            List of Document objects
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file type is not supported
            Exception: If processing fails
        """
        # TODO: Implement file processing.
        # Expected steps:
        # 1) Validate `file_path` exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        all_docs = []
        if is_supported_file(file_path=file_path):
            file_type : str = detect_file_type(file_path=file_path)
            match file_type.upper():
                case "PDF":
                    all_docs.extend(self.pdf_loader.load(file_path=file_path))
                case "TXT":
                    all_docs.extend(self.text_loader.load(file_path=file_path))
                case "HTML":
                    all_docs.extend(self.html_loader.load(file_path=file_path))
                case _:
                    raise FileNotFoundError(f"File cannot be proccessed to ingestion.")
        else:
            raise FileNotFoundError(f"The Given File Extension {detect_file_type(file_path)} is not Supported")
        
        return all_docs

        # 2) Detect file type via `detect_file_type`
        # 3) Route to the appropriate loader service:
        #    - PDF: `self.pdf_loader.load(file_path)`
        #    - TXT: `self.text_loader.load(file_path)`
        #    - HTML/HTM: `self.html_loader.load(file_path)`
        # 4) Return a list of `Document`
        # 5) Raise informative errors for missing files or unsupported types
        raise NotImplementedError(
            "process_file() not implemented. Validate path, detect type, route to loader, return List[Document]."
        )
    
    def process_url(self, url: str, header_template: Optional[dict] = None) -> List[Document]:
        """
        Process a web URL and return Document objects.
        
        Args:
            url: URL of the web page to process
            header_template: Optional headers for the request
            
        Returns:
            List of Document objects
            
        Raises:
            Exception: If processing fails
        """
        # TODO: Implement URL processing.
        # Expected:
        # - Use `self.web_loader.load(url, header_template)` to fetch and parse
        # - Return a list of `Document`
        # - Add basic logging and error handling
        raise NotImplementedError(
            "process_url() not implemented. Use web_loader.load(url, header_template) and return List[Document]."
        )
    
    def process_directory(self, directory: str, recursive: bool = False) -> List[Document]:
        """
        Process all supported files in a directory.
        
        Args:
            directory: Directory path to process
            recursive: Whether to process subdirectories recursively
            
        Returns:
            List of Document objects from all processed files
        """
        # TODO: Implement directory processing.
        # Expected:
        # - Validate directory exists
        if not os.path.isdir(directory):
            raise NotADirectoryError(f"The Directory: {directory} is not valid")
        # - Iterate over supported files (optionally recursively)
        SUPPORTED = {".pdf", ".txt", ".html", ".htm"}

        all_docs = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                if os.path.splitext(file)[1].lower() in SUPPORTED:
                    full_path = os.path.join(root, file)
                    docs = self.process_file(full_path)
                    all_docs.extend(docs)
        # - Use `self.process_file` for each file
        # - Collect and return all `Document` objects
        return all_docs
        raise NotImplementedError(
            "process_directory() not implemented. Validate dir, iterate supported files (optional recursion), aggregate results."
        )


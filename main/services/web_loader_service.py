"""
Web Document Loader Service

This service handles loading documents from web pages using WebBaseLoader.
Provides a clean, reusable interface for web document loading operations.
"""

from typing import List, Optional, Union
import logging
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document
import bs4

logger = logging.getLogger(__name__)


class WebLoaderService:
    """Service for loading documents from web pages."""
    
    def __init__(self):
        """Initialize the web loader service."""
        pass
    
    def _load_single_web_page(self, url: str) -> List[Document]:
        """
        Internal method to load a single web page safely.
        
        Args:
            url: URL of the web page to load
            
        Returns:
            List of Document objects (empty list if loading fails)
        """
        # TODO: Implement single web page loading.
        # Expected steps:
        # 1) Create WebBaseLoader with `web_paths=[url]` and bs4.SoupStrainer to limit parsed content
        # 2) Call `load()` to get List[Document]
        # 3) Add basic logging and handle errors gracefully (return [] on failure)
        raise NotImplementedError(
            "_load_single_web_page() not implemented. Use WebBaseLoader with SoupStrainer and return documents."
        )
    
    def load_web_pages(
        self,
        source: Optional[Union[str, List[str]]] = None
    ) -> List[Document]:
        """
        Load web page(s) safely. Handles single URL or multiple URLs.
        
        Args:
            source: Single URL string, or list of URL strings.
            
        Returns:
            List of Document objects (empty list if loading fails)
            
        Examples:
            # Load single URL
            docs = service.load_web_pages("https://example.com")
            
            # Load multiple URLs
            docs = service.load_web_pages(["https://example.com", "https://another.com"])
        """
        # TODO: Implement multi-page web loading.
        # Expected:
        # - If `source` is None, log and return []
        # - Normalize to a List[str] of URLs
        # - Iterate URLs, delegate to `_load_single_web_page(url)`, and aggregate results
        # - Return aggregated List[Document]
        raise NotImplementedError(
            "load_web_pages() not implemented. Normalize URLs, delegate to _load_single_web_page, and aggregate."
        )

    def load(self, url: str, header_template: Optional[dict] = None) -> List[Document]:
        """
        Backward-compatible wrapper for existing callers. 'header_template' is ignored.
        """
        # TODO: Implement wrapper delegation.
        # Expected:
        # - Ignore `header_template` for compatibility
        # - Delegate to `_load_single_web_page(url)` and return its result
        raise NotImplementedError(
            "load() not implemented. Delegate to _load_single_web_page(url)."
        )


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

try:
    import bs4
except ImportError:
    bs4 = None

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
        try:
            documents = []
            if bs4 is not None:
                try:
                    web_loader = WebBaseLoader(
                        web_paths=[url],
                         bs_kwargs={
                            "parse_only": bs4.SoupStrainer(
                            name=["article", "main", "section"]
                        )
                        }
                    )
                    documents = web_loader.load()
                    
                    # Check if filtered content is empty, fallback to basic loader
                    if documents and len(documents[0].page_content.strip()) == 0:
                        logger.warning("Filtered content is empty, falling back to basic loader")
                        documents = []
                except Exception as filter_error:
                    logger.warning(f"Filtered loading failed: {filter_error}, trying basic loader")
                    documents = []
            if not documents:
                web_loader = WebBaseLoader(web_paths=[url])
                documents = web_loader.load()
            
            logger.info(f"Loaded {len(documents)} document(s) from web: {url}")
            if documents:
                logger.info(f"Content length: {len(documents[0].page_content):,} characters")
            return documents
        except Exception as e:
            logger.error(f"Error loading web page {url}: {e}")
            logger.error(f"This may be due to network issues or site restrictions")
            return []


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
        all_documents: List[Document] = []
        
        if source is None:
            logger.warning("No URL provided")
            return []
        
        # Convert single URL to list for uniform processing
        urls: List[str] = source if isinstance(source, list) else [source]
        
        logger.info(f"Loading {len(urls)} web page(s)...")
        
        for url in urls:
            logger.info(f"URL: {url}")
            documents = self._load_single_web_page(url)
            all_documents.extend(documents)
        
        return all_documents

        raise NotImplementedError(
            "load_web_pages() not implemented. Normalize URLs, delegate to _load_single_web_page, and aggregate."
        )

    def load(self, url: str, header_template: Optional[dict] = None) -> List[Document]:
        """
        Backward-compatible wrapper for existing callers. 'header_template' is ignored.
        """
        # Ignore `header_template` for compatibility and delegate to the single-page loader
        try:
            logger.info(f"load() wrapper called for URL: {url}")
            return self._load_single_web_page(url)
        except Exception as e:
            logger.error(f"load() wrapper failed for URL {url}: {e}")
            return []


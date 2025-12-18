"""Table Extraction Service Module
Handles table extraction operations from markdown text.

This module provides:
- Markdown table extraction interface
"""
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


def find_markdown_tables(md_text: str) -> List[Tuple[int, int, str]]:
    """
    Extract markdown table blocks from text.

    Returns a list of tuples: (start_index, end_index, table_string)
    
    Args:
        md_text: Markdown text to search for tables
        
    Returns:
        List of tuples containing (start_char_index, end_char_index, table_markdown)
    """
    logger.info("Extracting markdown tables (boilerplate)")

    # TODO: Find and extract markdown table blocks from `md_text`.
    # HINT: Split text into lines and identify contiguous blocks that represent a table.
    # HINT: For each detected table block, return a tuple of:
    #   - start_char_index (in the original string)
    #   - end_char_index (in the original string)
    #   - table_markdown (the exact markdown table text)
    # HINT: Return an empty list if no tables exist.
    # Your code here:
    raise NotImplementedError(
        "find_markdown_tables method is not implemented yet. Please complete the implementation."
    )

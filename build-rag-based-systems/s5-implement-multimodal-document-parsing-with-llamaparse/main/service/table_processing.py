"""Table Processing Service Module
Handles table summarization and node creation from extracted tables.

This module provides:
- Table summarization interface
- Node creation interface for table summaries
"""
import logging
from typing import List, Dict, Any

from llama_index.core.schema import TextNode
from llama_index.llms.azure_openai import AzureOpenAI

logger = logging.getLogger(__name__)


def summarize_table(llm: AzureOpenAI, table_md: str) -> str:
    """
    Summarize a markdown table into a natural language description.
    
    Args:
        llm: The language model instance
        table_md: Markdown table string
        
    Returns:
        Single-sentence summary of the table
    """
    logger.info("Summarizing table (boilerplate)")

    # TODO: Summarize the markdown table into a single-sentence natural language summary.
    # HINT: Use the provided `llm` to generate the summary text.
    # HINT: Keep the summary concise and factual (include key figures/relationships).
    # HINT: Decide how you want to handle model/content-filter failures (retry/fallback).
    # Your code here:
    if not table_md or not table_md.strip():
        return ""
        
        # Truncate very long table data to avoid token limits and content filter issues
    max_table_length = 5000  # characters
    truncated_table = table_md[:max_table_length]
    if len(table_md) > max_table_length:
        truncated_table += "\n[... table truncated ...]"
        logger.warning(f"Table data truncated from {len(table_md)} to {max_table_length} characters")
        
    prompt = f"""You are a data analyst. Analyze the following table and provide a clear, factual summary.

        Focus on:
        - Key numerical values and figures
        - Important trends or patterns
        - Significant data points

        Table data:
        {truncated_table}

        Provide a concise summary of the key information in this table."""
        
    try:
        response = llm.complete(prompt)
        summary = str(response).strip()
        return summary
    except Exception as e:
        logger.error(f"Unexpected error generating table summary: {e}")
        raise
        


def build_nodes_from_tables(
    source_name: str, 
    table_markdowns: List[str], 
    llm: AzureOpenAI,
    additional_metadata: Dict[str, Any] = None
) -> List[TextNode]:
    """
    Build TextNode objects from table markdowns with summaries.
    
    Args:
        source_name: Name of the source document
        table_markdowns: List of markdown table strings
        llm: Language model instance for summarization
        additional_metadata: Optional additional metadata to include
        
    Returns:
        List of TextNode objects with table summaries
    """
    logger.info("Building nodes from tables (boilerplate)")

    # TODO: Create TextNode objects from table markdowns.
    # HINT: For each table markdown:
    #   - create a summary using `summarize_table(llm, table_md)`
    #   - create a TextNode(text=summary, metadata=...)
    # HINT: Include at least these metadata fields:
    #   - source: source_name
    #   - content_type: "table_summary"
    #   - table_index: incremental index
    # HINT: Merge `additional_metadata` into each node's metadata if provided.
    # Your code here:

    all_nodes = []
    
    for i,mds in enumerate(table_markdowns,start=0):
        node_metadata = {}
        node_metadata["content_type"] = "table_summary"
        node_metadata["source"] = source_name
        node_metadata["table_index"] = i

        # Generate summary and coerce to a safe string value
        summary = summarize_table(llm=llm, table_md=mds)
        if summary is None:
            summary = "[table summary unavailable]"
        elif not isinstance(summary, str):
            summary = str(summary)
        elif not summary.strip():
            summary = "[no table content]"

        merged_metadata = {**node_metadata, **(additional_metadata or {})}
        all_nodes.append(TextNode(
            text=summary,
            metadata=merged_metadata,
        ))
        
    return all_nodes

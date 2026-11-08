"""Model Context Protocol integration for external legal databases."""

from app.mcp.connection_manager import MCPConnectionManager
from app.mcp.models import ExternalLegalHit, ExternalSearchResult, MCPServerConfig
from app.mcp.search import ExternalLegalSearchService

__all__ = [
    "ExternalLegalHit",
    "ExternalLegalSearchService",
    "ExternalSearchResult",
    "MCPConnectionManager",
    "MCPServerConfig",
]

"""MCP-specific exception types."""


class MCPError(Exception):
    """Base MCP integration error."""


class MCPConnectionError(MCPError):
    """Failed to establish or maintain an MCP server connection."""


class MCPAuthenticationError(MCPError):
    """Authentication to an MCP server failed."""


class MCPSearchError(MCPError):
    """A legal search call against an MCP server failed."""


class MCPServerConfigError(MCPError):
    """Invalid MCP server configuration."""

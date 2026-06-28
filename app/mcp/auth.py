"""Authentication helpers for MCP server connections."""

from __future__ import annotations

from app.mcp.exceptions import MCPAuthenticationError
from app.mcp.models import MCPAuthConfig, MCPAuthType


def build_auth_headers(auth: MCPAuthConfig) -> dict[str, str]:
    """
    Build HTTP headers for SSE / Streamable HTTP MCP transports.

    Raises MCPAuthenticationError when credentials are required but missing.
    """
    if auth.auth_type == MCPAuthType.NONE:
        return {}

    token = auth.resolve_token()
    if not token:
        env_hint = f" (env: {auth.token_env})" if auth.token_env else ""
        raise MCPAuthenticationError(
            f"Missing credentials for MCP authentication{env_hint}."
        )

    if auth.auth_type == MCPAuthType.BEARER:
        return {auth.header_name: f"Bearer {token}"}

    if auth.auth_type == MCPAuthType.API_KEY:
        return {auth.api_key_header: token}

    raise MCPAuthenticationError(f"Unsupported auth type: {auth.auth_type}")


def merge_env_with_auth(
    base_env: dict[str, str] | None,
    auth: MCPAuthConfig,
) -> dict[str, str] | None:
    """Inject resolved token into stdio subprocess environment when configured."""
    if auth.auth_type == MCPAuthType.NONE:
        return base_env

    token = auth.resolve_token()
    if not token:
        return base_env

    merged = dict(base_env or {})
    if auth.token_env:
        merged[auth.token_env] = token
    return merged

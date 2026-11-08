"""Data models for MCP legal database integration."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal


class MCPTransport(StrEnum):
    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable_http"


class MCPAuthType(StrEnum):
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"


@dataclass(frozen=True)
class MCPAuthConfig:
    """Authentication settings for an MCP server connection."""

    auth_type: MCPAuthType = MCPAuthType.NONE
    token: str = ""
    token_env: str = ""
    header_name: str = "Authorization"
    api_key_header: str = "X-API-Key"

    def resolve_token(self) -> str:
        if self.token:
            return self.token
        if self.token_env:
            return os.environ.get(self.token_env, "")
        return ""


@dataclass(frozen=True)
class MCPServerConfig:
    """Configuration for a single external legal MCP server."""

    name: str
    transport: MCPTransport
    enabled: bool = True
    search_tool: str = "search_legal_documents"
    search_arg: str = "query"
    max_results: int = 5
    timeout_seconds: float = 30.0
    auth: MCPAuthConfig = field(default_factory=MCPAuthConfig)
    # stdio
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None
    # network transports
    url: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> MCPServerConfig:
        auth_raw = raw.get("auth") or {}
        auth = MCPAuthConfig(
            auth_type=MCPAuthType(auth_raw.get("type", MCPAuthType.NONE)),
            token=str(auth_raw.get("token", "")),
            token_env=str(auth_raw.get("token_env", "")),
            header_name=str(auth_raw.get("header_name", "Authorization")),
            api_key_header=str(auth_raw.get("api_key_header", "X-API-Key")),
        )
        return cls(
            name=str(raw["name"]),
            transport=MCPTransport(raw.get("transport", MCPTransport.SSE)),
            enabled=bool(raw.get("enabled", True)),
            search_tool=str(raw.get("search_tool", "search_legal_documents")),
            search_arg=str(raw.get("search_arg", "query")),
            max_results=int(raw.get("max_results", 5)),
            timeout_seconds=float(raw.get("timeout_seconds", 30.0)),
            auth=auth,
            command=str(raw.get("command", "")),
            args=[str(item) for item in raw.get("args", [])],
            env={str(k): str(v) for k, v in (raw.get("env") or {}).items()},
            cwd=raw.get("cwd"),
            url=str(raw.get("url", "")),
        )


def parse_mcp_servers(raw: str | list[dict[str, Any]]) -> list[MCPServerConfig]:
    """Parse MCP server definitions from JSON string or list."""
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return []
        payload = json.loads(stripped)
    else:
        payload = raw

    if not isinstance(payload, list):
        raise ValueError("MCP_SERVERS must be a JSON array of server configs.")

    return [MCPServerConfig.from_dict(item) for item in payload]


@dataclass(frozen=True)
class ExternalLegalHit:
    """Normalized legal document hit from an external MCP database."""

    title: str
    content: str
    source_name: str
    source_type: str = "external_legal"
    entity_type: str = "legal_document"
    entity_id: str = ""
    citation: str = ""
    jurisdiction: str = ""
    url: str = ""
    score: float = 0.75
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExternalSearchResult:
    """Aggregated search output from one or more MCP servers."""

    hits: list[ExternalLegalHit] = field(default_factory=list)
    servers_queried: list[str] = field(default_factory=list)
    servers_failed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_count(self) -> int:
        return len(self.hits)

    @property
    def had_failures(self) -> bool:
        return bool(self.servers_failed or self.errors)

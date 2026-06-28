"""Low-level MCP client wrapper for legal database servers."""

from __future__ import annotations

import json
import logging
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any

from mcp import ClientSession, StdioServerParameters

from app.mcp.auth import build_auth_headers, merge_env_with_auth
from app.mcp.exceptions import (
    MCPAuthenticationError,
    MCPConnectionError,
    MCPSearchError,
    MCPServerConfigError,
)
from app.mcp.models import ExternalLegalHit, MCPServerConfig, MCPTransport
from app.mcp.retry import MCPRetryPolicy

logger = logging.getLogger(__name__)


@dataclass
class MCPClient:
    """
    MCP client for a single legal database server.

    Manages transport lifecycle and exposes tool-based search operations.
    """

    config: MCPServerConfig
    retry_policy: MCPRetryPolicy = field(default_factory=MCPRetryPolicy)
    _exit_stack: AsyncExitStack = field(default_factory=AsyncExitStack, init=False)
    _session: ClientSession | None = field(default=None, init=False)
    _connected: bool = field(default=False, init=False)

    async def connect(self) -> None:
        """Establish an MCP session to the configured server."""
        if self._connected and self._session is not None:
            return

        self._validate_config()

        try:
            read_stream, write_stream = await self._open_transport()
            session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()
            self._session = session
            self._connected = True
            logger.info("Connected to MCP server '%s'", self.config.name)
        except MCPAuthenticationError:
            raise
        except Exception as exc:
            await self.disconnect()
            raise MCPConnectionError(
                f"Failed to connect to MCP server '{self.config.name}': {exc}"
            ) from exc

    async def disconnect(self) -> None:
        """Tear down the MCP session and transport."""
        self._session = None
        self._connected = False
        await self._exit_stack.aclose()
        self._exit_stack = AsyncExitStack()

    async def search(self, query: str) -> list[ExternalLegalHit]:
        """Call the configured search tool and normalize results."""
        search_fn = self.retry_policy.wrap(self._search_once)
        return await search_fn(query)

    async def _search_once(self, query: str) -> list[ExternalLegalHit]:
        await self.connect()
        if self._session is None:
            raise MCPConnectionError(
                f"MCP session unavailable for server '{self.config.name}'."
            )

        arguments = {
            self.config.search_arg: query,
            "limit": self.config.max_results,
            "max_results": self.config.max_results,
        }

        try:
            result = await self._session.call_tool(
                self.config.search_tool,
                arguments=arguments,
            )
        except Exception as exc:
            raise MCPSearchError(
                f"Tool '{self.config.search_tool}' failed on "
                f"'{self.config.name}': {exc}"
            ) from exc

        return _parse_tool_result(result, self.config)

    async def _open_transport(self):
        transport = self.config.transport

        if transport == MCPTransport.STDIO:
            if not self.config.command:
                raise MCPServerConfigError(
                    f"Server '{self.config.name}' requires 'command' for stdio."
                )
            from mcp.client.stdio import stdio_client

            params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=merge_env_with_auth(self.config.env, self.config.auth),
                cwd=self.config.cwd,
            )
            return await self._exit_stack.enter_async_context(stdio_client(params))

        if transport == MCPTransport.SSE:
            if not self.config.url:
                raise MCPServerConfigError(
                    f"Server '{self.config.name}' requires 'url' for SSE."
                )
            from mcp.client.sse import sse_client

            headers = build_auth_headers(self.config.auth)
            return await self._exit_stack.enter_async_context(
                sse_client(
                    self.config.url,
                    headers=headers or None,
                    timeout=self.config.timeout_seconds,
                )
            )

        if transport == MCPTransport.STREAMABLE_HTTP:
            if not self.config.url:
                raise MCPServerConfigError(
                    f"Server '{self.config.name}' requires 'url' for streamable_http."
                )
            from mcp.client.streamable_http import streamablehttp_client

            headers = build_auth_headers(self.config.auth)
            transport = await self._exit_stack.enter_async_context(
                streamablehttp_client(
                    self.config.url,
                    headers=headers or None,
                    timeout=self.config.timeout_seconds,
                )
            )
            read_stream, write_stream, *_ = transport
            return read_stream, write_stream

        raise MCPServerConfigError(
            f"Unsupported transport '{transport}' for server '{self.config.name}'."
        )

    def _validate_config(self) -> None:
        if self.config.transport == MCPTransport.STDIO and not self.config.command:
            raise MCPServerConfigError(
                f"Server '{self.config.name}' is missing stdio command."
            )
        if self.config.transport in {MCPTransport.SSE, MCPTransport.STREAMABLE_HTTP}:
            if not self.config.url:
                raise MCPServerConfigError(
                    f"Server '{self.config.name}' is missing connection URL."
                )


def _parse_tool_result(result: Any, config: MCPServerConfig) -> list[ExternalLegalHit]:
    """Convert MCP tool output into normalized legal hits."""
    raw_items: list[Any] = []

    if hasattr(result, "structuredContent") and result.structuredContent:
        structured = result.structuredContent
        if isinstance(structured, dict):
            raw_items = _extract_items_from_payload(structured)
        elif isinstance(structured, list):
            raw_items = structured

    if not raw_items and hasattr(result, "content"):
        for block in result.content or []:
            text = getattr(block, "text", None)
            if not text:
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                raw_items.append({"title": config.name, "content": text})
                continue

            if isinstance(parsed, list):
                raw_items.extend(parsed)
            elif isinstance(parsed, dict):
                raw_items.extend(_extract_items_from_payload(parsed))

    hits: list[ExternalLegalHit] = []
    for index, item in enumerate(raw_items[: config.max_results]):
        if isinstance(item, ExternalLegalHit):
            hits.append(item)
            continue
        if not isinstance(item, dict):
            hits.append(
                ExternalLegalHit(
                    title=f"{config.name} result {index + 1}",
                    content=str(item),
                    source_name=config.name,
                )
            )
            continue
        hits.append(_dict_to_hit(item, config, index))

    return hits


def _extract_items_from_payload(payload: dict[str, Any]) -> list[Any]:
    for key in ("results", "hits", "documents", "items", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return [payload]


def _dict_to_hit(item: dict[str, Any], config: MCPServerConfig, index: int) -> ExternalLegalHit:
    title = str(
        item.get("title")
        or item.get("name")
        or item.get("case_name")
        or item.get("citation")
        or f"{config.name} result {index + 1}"
    )
    content = str(
        item.get("content")
        or item.get("text")
        or item.get("summary")
        or item.get("snippet")
        or item.get("abstract")
        or title
    )
    entity_id = str(
        item.get("id")
        or item.get("entity_id")
        or item.get("document_id")
        or f"{config.name}-{index}"
    )
    return ExternalLegalHit(
        title=title,
        content=content,
        source_name=config.name,
        source_type=str(item.get("source_type", "external_legal")),
        entity_type=str(item.get("entity_type", "legal_document")),
        entity_id=entity_id,
        citation=str(item.get("citation", "")),
        jurisdiction=str(item.get("jurisdiction", "")),
        url=str(item.get("url", "")),
        score=float(item.get("score", item.get("relevance", 0.75))),
        metadata={
            key: value
            for key, value in item.items()
            if key
            not in {
                "title",
                "name",
                "case_name",
                "content",
                "text",
                "summary",
                "snippet",
                "abstract",
                "id",
                "entity_id",
                "document_id",
                "citation",
                "jurisdiction",
                "url",
                "score",
                "relevance",
                "source_type",
                "entity_type",
            }
        },
    )

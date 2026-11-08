"""Connection manager for multiple external legal MCP servers."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from app.mcp.client import MCPClient
from app.mcp.exceptions import MCPAuthenticationError, MCPConnectionError, MCPSearchError
from app.mcp.models import MCPServerConfig
from app.mcp.retry import MCPRetryPolicy

logger = logging.getLogger(__name__)


@dataclass
class MCPConnectionManager:
    """
    Manages MCP client connections across configured legal databases.

    Provides lazy connection, per-server isolation, and graceful shutdown.
    """

    servers: list[MCPServerConfig]
    retry_policy: MCPRetryPolicy = field(default_factory=MCPRetryPolicy)
    _clients: dict[str, MCPClient] = field(default_factory=dict, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    @property
    def enabled_servers(self) -> list[MCPServerConfig]:
        return [server for server in self.servers if server.enabled]

    def get_client(self, server: MCPServerConfig) -> MCPClient:
        existing = self._clients.get(server.name)
        if existing is not None:
            return existing

        client = MCPClient(config=server, retry_policy=self.retry_policy)
        self._clients[server.name] = client
        return client

    async def connect_all(self) -> dict[str, str | None]:
        """Eagerly connect all enabled servers; returns per-server status."""
        statuses: dict[str, str | None] = {}
        for server in self.enabled_servers:
            try:
                await self.get_client(server).connect()
                statuses[server.name] = None
            except (MCPConnectionError, MCPAuthenticationError) as exc:
                statuses[server.name] = str(exc)
                logger.warning(
                    "Could not connect to MCP server '%s': %s",
                    server.name,
                    exc,
                )
        return statuses

    async def disconnect_all(self) -> None:
        """Close all active MCP sessions."""
        async with self._lock:
            for client in self._clients.values():
                try:
                    await client.disconnect()
                except Exception as exc:
                    logger.debug("Error disconnecting MCP client: %s", exc)
            self._clients.clear()

    async def search_all(
        self,
        query: str,
        *,
        server_names: list[str] | None = None,
    ) -> tuple[list, list[str], list[str]]:
        """
        Search all (or selected) enabled servers in parallel.

        Returns (hits, queried_server_names, error_messages).
        Failures on individual servers do not abort the overall search.
        """
        from app.mcp.models import ExternalLegalHit

        targets = [
            server
            for server in self.enabled_servers
            if server_names is None or server.name in server_names
        ]
        if not targets:
            return [], [], []

        async def _search_one(server: MCPServerConfig) -> tuple[str, list[ExternalLegalHit], str | None]:
            client = self.get_client(server)
            try:
                hits = await client.search(query)
                return server.name, hits, None
            except (MCPConnectionError, MCPAuthenticationError, MCPSearchError) as exc:
                logger.warning(
                    "MCP search failed for '%s': %s",
                    server.name,
                    exc,
                )
                try:
                    await client.disconnect()
                except Exception:
                    pass
                self._clients.pop(server.name, None)
                return server.name, [], str(exc)
            except Exception as exc:
                logger.exception(
                    "Unexpected MCP search error for '%s'",
                    server.name,
                )
                return server.name, [], str(exc)

        results = await asyncio.gather(*(_search_one(server) for server in targets))

        hits: list[ExternalLegalHit] = []
        queried: list[str] = []
        errors: list[str] = []

        for server_name, server_hits, error in results:
            queried.append(server_name)
            hits.extend(server_hits)
            if error:
                errors.append(f"{server_name}: {error}")

        hits.sort(key=lambda item: item.score, reverse=True)
        return hits, queried, errors

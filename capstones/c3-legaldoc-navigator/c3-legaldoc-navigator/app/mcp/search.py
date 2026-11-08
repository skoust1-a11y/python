"""High-level search API over external legal MCP databases."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.mcp.connection_manager import MCPConnectionManager
from app.mcp.models import ExternalSearchResult, MCPServerConfig
from app.mcp.retry import MCPRetryPolicy

logger = logging.getLogger(__name__)


@dataclass
class ExternalLegalSearchService:
    """
    Search facade for external legal databases exposed via MCP.

    Handles disabled state, empty configuration, and partial failures gracefully.
    """

    servers: list[MCPServerConfig] = field(default_factory=list)
    enabled: bool = False
    retry_policy: MCPRetryPolicy = field(default_factory=MCPRetryPolicy)
    _manager: MCPConnectionManager | None = field(default=None, init=False)

    def _get_manager(self) -> MCPConnectionManager:
        if self._manager is None:
            self._manager = MCPConnectionManager(
                servers=self.servers,
                retry_policy=self.retry_policy,
            )
        return self._manager

    @property
    def is_available(self) -> bool:
        return self.enabled and bool(self._get_manager().enabled_servers)

    async def search(
        self,
        query: str,
        *,
        server_names: list[str] | None = None,
    ) -> ExternalSearchResult:
        """
        Search external legal MCP databases.

        When MCP is disabled or unconfigured, returns an empty result without error.
        Individual server failures are captured in ``servers_failed`` / ``errors``.
        """
        if not self.is_available:
            logger.debug("External MCP search skipped (disabled or no servers).")
            return ExternalSearchResult()

        manager = self._get_manager()
        hits, queried, errors = await manager.search_all(
            query,
            server_names=server_names,
        )

        failed = [
            name
            for name, error in (
                (entry.split(":", 1)[0], entry)
                for entry in errors
            )
            if error
        ]

        if errors:
            logger.info(
                "External MCP search completed with partial failures: %s",
                "; ".join(errors),
            )

        return ExternalSearchResult(
            hits=hits,
            servers_queried=queried,
            servers_failed=failed,
            errors=errors,
        )

    async def shutdown(self) -> None:
        """Release all MCP connections."""
        if self._manager is not None:
            await self._manager.disconnect_all()
            self._manager = None

"""Unit tests for MCP legal database integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mcp.auth import build_auth_headers
from app.mcp.client import MCPClient, _parse_tool_result
from app.mcp.connection_manager import MCPConnectionManager
from app.mcp.exceptions import MCPAuthenticationError
from app.mcp.models import (
    ExternalLegalHit,
    MCPAuthConfig,
    MCPAuthType,
    MCPServerConfig,
    MCPTransport,
    parse_mcp_servers,
)
from app.mcp.retry import MCPRetryPolicy
from app.mcp.search import ExternalLegalSearchService
from app.rag.merge import external_results_to_nodes, merge_retrieval_results
from app.services.sql_query_executor import SqlRetrievalResult


class TestMCPAuth:
    def test_bearer_header(self) -> None:
        auth = MCPAuthConfig(auth_type=MCPAuthType.BEARER, token="secret-token")
        assert build_auth_headers(auth) == {"Authorization": "Bearer secret-token"}

    def test_api_key_header(self) -> None:
        auth = MCPAuthConfig(
            auth_type=MCPAuthType.API_KEY,
            token="key-123",
            api_key_header="X-Legal-Key",
        )
        assert build_auth_headers(auth) == {"X-Legal-Key": "key-123"}

    def test_missing_credentials_raises(self) -> None:
        auth = MCPAuthConfig(auth_type=MCPAuthType.BEARER, token_env="MISSING_ENV_VAR")
        with pytest.raises(MCPAuthenticationError):
            build_auth_headers(auth)


class TestMCPServerConfig:
    def test_parse_servers_from_json_string(self) -> None:
        raw = """
        [
          {
            "name": "courtlistener",
            "transport": "sse",
            "url": "https://example.com/mcp/sse",
            "search_tool": "search_cases",
            "auth": {"type": "bearer", "token_env": "COURTLISTENER_API_KEY"}
          }
        ]
        """
        servers = parse_mcp_servers(raw)
        assert len(servers) == 1
        assert servers[0].name == "courtlistener"
        assert servers[0].transport == MCPTransport.SSE
        assert servers[0].auth.token_env == "COURTLISTENER_API_KEY"


class TestMCPClientParsing:
    def test_parse_structured_tool_result(self) -> None:
        config = MCPServerConfig(
            name="test-db",
            transport=MCPTransport.SSE,
            url="https://example.com",
        )
        result = MagicMock()
        result.structuredContent = {
            "results": [
                {
                    "title": "Smith v. Jones",
                    "content": "Contract dispute ruling.",
                    "citation": "123 F.3d 456",
                    "jurisdiction": "US-Federal",
                    "score": 0.92,
                }
            ]
        }
        result.content = []

        hits = _parse_tool_result(result, config)
        assert len(hits) == 1
        assert hits[0].title == "Smith v. Jones"
        assert hits[0].citation == "123 F.3d 456"
        assert hits[0].score == 0.92

    def test_parse_json_text_content(self) -> None:
        config = MCPServerConfig(
            name="test-db",
            transport=MCPTransport.SSE,
            url="https://example.com",
        )
        block = MagicMock()
        block.text = '[{"title": "Statute A", "content": "Section 1 text."}]'
        result = MagicMock()
        result.structuredContent = None
        result.content = [block]

        hits = _parse_tool_result(result, config)
        assert len(hits) == 1
        assert hits[0].title == "Statute A"


class TestExternalMerge:
    def test_external_nodes_merge_with_vector_and_sql(self) -> None:
        from llama_index.core.schema import NodeWithScore, TextNode

        vector = NodeWithScore(
            node=TextNode(
                id_="vec-1",
                text="local contract clause",
                metadata={
                    "document_id": "doc-1",
                    "chunk_index": 0,
                    "source_type": "vector",
                },
            ),
            score=0.9,
        )
        external_hits = [
            ExternalLegalHit(
                title="External Case",
                content="Relevant precedent from external DB.",
                source_name="courtlistener",
                entity_id="case-99",
                score=0.88,
            )
        ]
        external_nodes = external_results_to_nodes(external_hits)

        merged, stats = merge_retrieval_results(
            [vector],
            SqlRetrievalResult(),
            external_nodes=external_nodes,
        )

        assert len(merged) == 2
        assert stats.external_input_count == 1
        source_types = {node.node.metadata["source_type"] for node in merged}
        assert "external_legal" in source_types


class TestExternalLegalSearchService:
    @pytest.mark.asyncio
    async def test_disabled_returns_empty(self) -> None:
        service = ExternalLegalSearchService(enabled=False)
        result = await service.search("termination clause")
        assert result.total_count == 0
        assert not result.had_failures

    @pytest.mark.asyncio
    async def test_partial_failure_is_graceful(self) -> None:
        servers = [
            MCPServerConfig(
                name="good-db",
                transport=MCPTransport.SSE,
                url="https://good.example.com",
                enabled=True,
            ),
            MCPServerConfig(
                name="bad-db",
                transport=MCPTransport.SSE,
                url="https://bad.example.com",
                enabled=True,
            ),
        ]
        service = ExternalLegalSearchService(servers=servers, enabled=True)

        good_hit = ExternalLegalHit(
            title="Good Result",
            content="Found externally.",
            source_name="good-db",
            entity_id="1",
        )

        async def fake_search_all(query, server_names=None):
            return [good_hit], ["good-db", "bad-db"], ["bad-db: connection refused"]

        with patch.object(
            MCPConnectionManager,
            "search_all",
            new=AsyncMock(side_effect=fake_search_all),
        ):
            result = await service.search("indemnity")

        assert result.total_count == 1
        assert result.had_failures
        assert "bad-db" in result.servers_failed


class TestMCPClientSearch:
    @pytest.mark.asyncio
    async def test_search_uses_retry_policy(self) -> None:
        config = MCPServerConfig(
            name="retry-db",
            transport=MCPTransport.SSE,
            url="https://example.com",
        )
        client = MCPClient(
            config=config,
            retry_policy=MCPRetryPolicy(max_attempts=1),
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.structuredContent = {
            "results": [{"title": "Hit", "content": "Body"}]
        }
        mock_result.content = []
        mock_session.call_tool.return_value = mock_result

        with patch.object(client, "connect", new=AsyncMock()):
            client._session = mock_session
            client._connected = True
            hits = await client.search("query")

        assert len(hits) == 1
        mock_session.call_tool.assert_awaited_once()

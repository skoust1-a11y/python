"""Unit tests for the LLM query router."""

import json

import pytest

from app.routing.models import RoutingResult
from app.routing.router import Router
from app.routing.routes import RouteDefinition, RouteRegistry


@pytest.fixture
def router() -> Router:
    return Router()


class TestRouterValidation:
    def test_parses_plain_json(self, router: Router) -> None:
        raw = json.dumps(
            {"route": "sql", "reason": "Needs contract filtering", "confidence": 0.92}
        )
        result = router._validate_decision(router._parse_response(raw))
        assert result == RoutingResult(
            route="sql",
            reason="Needs contract filtering",
            confidence=0.92,
        )

    def test_parses_json_code_fence(self, router: Router) -> None:
        raw = '```json\n{"route":"hybrid","reason":"Both text and cases","confidence":0.88}\n```'
        result = router._validate_decision(router._parse_response(raw))
        assert result.route == "hybrid"
        assert result.confidence == 0.88

    def test_unknown_route_falls_back(self, router: Router) -> None:
        raw = json.dumps({"route": "graph", "reason": "unknown", "confidence": 0.9})
        result = router._validate_decision(router._parse_response(raw))
        assert result.route == "rag"
        assert result.confidence == 0.0
        assert "Fell back" in result.reason

    def test_low_confidence_falls_back(self) -> None:
        router = Router(min_confidence=0.8)
        raw = json.dumps({"route": "sql", "reason": "maybe", "confidence": 0.4})
        result = router._validate_decision(router._parse_response(raw))
        assert result.route == "rag"
        assert result.confidence == 0.0

    def test_result_serializes_to_json(self, router: Router) -> None:
        raw = json.dumps({"route": "rag", "reason": "Summarization task", "confidence": 0.95})
        result = router._validate_decision(router._parse_response(raw))
        payload = json.loads(result.model_dump_json())
        assert payload == {
            "route": "rag",
            "reason": "Summarization task",
            "confidence": 0.95,
        }


class TestRouteRegistry:
    def test_register_new_route(self) -> None:
        registry = RouteRegistry()
        registry.register(
            RouteDefinition(
                name="graph",
                description="Knowledge-graph traversal",
                examples=("Who is party to contract X?",),
            )
        )
        router = Router(registry=registry, default_route="graph")
        assert "graph" in router.registry.names()
        assert router._default_route == "graph"

    def test_duplicate_route_raises(self) -> None:
        registry = RouteRegistry()
        route = RouteDefinition(name="rag", description="test")
        registry.register(route)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(route)

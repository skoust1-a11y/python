"""LLM-powered query router — classifies queries into RAG, SQL, or Hybrid paths."""

import json
import re
from typing import Any

from llama_index.core.llms import ChatMessage, MessageRole

from app.core.config import settings
from app.core.exceptions import RouterError
from app.prompts.templates import (
    QUERY_ROUTING_SYSTEM_PROMPT,
    QUERY_ROUTING_USER_PROMPT_TEMPLATE,
)
from app.routing.models import RoutingResult
from app.routing.routes import RouteRegistry, default_route_registry
from app.services.llm_service import LLMService


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


class Router:
    """Classify user queries into retrieval paths using an LLM."""

    def __init__(
        self,
        llm_service: LLMService | None = None,
        registry: RouteRegistry | None = None,
        *,
        default_route: str = "rag",
        min_confidence: float = 0.0,
    ) -> None:
        self._llm_service = llm_service or LLMService()
        self._registry = registry or default_route_registry()
        self._default_route = default_route.lower()
        self._min_confidence = min_confidence

        if self._registry.get(self._default_route) is None:
            raise ValueError(
                f"Default route '{self._default_route}' is not registered"
            )

    @property
    def registry(self) -> RouteRegistry:
        return self._registry

    def register_route(self, name: str, description: str, examples: tuple[str, ...] = ()) -> None:
        """Register an additional route for future classification support."""
        from app.routing.routes import RouteDefinition

        self._registry.register(
            RouteDefinition(name=name.lower(), description=description, examples=examples)
        )

    async def route(
        self,
        query: str,
        *,
        provider: str | None = None,
    ) -> RoutingResult:
        """Classify a user query and return a routing decision with confidence."""
        query = query.strip()
        if not query:
            raise RouterError("Query must not be empty")

        llm = self._llm_service.get_llm(provider)
        messages = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=QUERY_ROUTING_SYSTEM_PROMPT.format(
                    routes=self._registry.format_for_prompt(),
                    valid_routes=", ".join(sorted(self._registry.names())),
                ),
            ),
            ChatMessage(
                role=MessageRole.USER,
                content=QUERY_ROUTING_USER_PROMPT_TEMPLATE.format(query=query),
            ),
        ]

        try:
            response = await llm.achat(messages)
            raw = (response.message.content or "").strip()
            parsed = self._parse_response(raw)
            return self._validate_decision(parsed)
        except RouterError:
            raise
        except Exception as exc:
            return self._fallback(f"Routing LLM unavailable ({exc})")

    def _parse_response(self, raw: str) -> dict[str, Any]:
        candidates = [raw]
        block_match = _JSON_BLOCK_RE.search(raw)
        if block_match:
            candidates.insert(0, block_match.group(1).strip())

        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data

        raise RouterError("LLM response did not contain valid JSON")

    def _validate_decision(self, data: dict[str, Any]) -> RoutingResult:
        route_raw = data.get("route")
        reason_raw = data.get("reason")
        confidence_raw = data.get("confidence")

        if not isinstance(route_raw, str) or not route_raw.strip():
            return self._fallback("LLM response missing a valid route field")

        route = route_raw.strip().lower()
        if route not in self._registry.names():
            return self._fallback(f"Unknown route '{route_raw}' returned by LLM")

        reason = reason_raw.strip() if isinstance(reason_raw, str) and reason_raw.strip() else (
            f"Query classified as {route}"
        )

        confidence = self._parse_confidence(confidence_raw)
        if confidence < self._min_confidence:
            return self._fallback(
                f"Confidence {confidence:.2f} below threshold {self._min_confidence:.2f}"
            )

        return RoutingResult(route=route, reason=reason, confidence=confidence)

    def _parse_confidence(self, value: Any) -> float:
        if value is None:
            return 0.5
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.5
        return max(0.0, min(1.0, score))

    def _fallback(self, reason: str) -> RoutingResult:
        return RoutingResult(
            route=self._default_route,
            reason=f"Fell back to {self._default_route}: {reason}",
            confidence=0.0,
        )

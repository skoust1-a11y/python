"""Extensible route definitions for query classification."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RouteDefinition:
    """Metadata for a single query route."""

    name: str
    description: str
    examples: tuple[str, ...] = field(default_factory=tuple)


class RouteRegistry:
    """Registry of available query routes. New routes can be registered at runtime."""

    def __init__(self) -> None:
        self._routes: dict[str, RouteDefinition] = {}

    def register(self, route: RouteDefinition) -> None:
        key = route.name.lower()
        if key in self._routes:
            raise ValueError(f"Route '{key}' is already registered")
        self._routes[key] = route

    def get(self, name: str) -> RouteDefinition | None:
        return self._routes.get(name.lower())

    def names(self) -> frozenset[str]:
        return frozenset(self._routes)

    def all(self) -> list[RouteDefinition]:
        return list(self._routes.values())

    def format_for_prompt(self) -> str:
        lines: list[str] = []
        for route in self.all():
            lines.append(f"- **{route.name}**: {route.description}")
            if route.examples:
                example_text = "; ".join(f'"{ex}"' for ex in route.examples)
                lines.append(f"  Examples: {example_text}")
        return "\n".join(lines)


def default_route_registry() -> RouteRegistry:
    """Build the default route registry with RAG, SQL, and Hybrid routes."""
    registry = RouteRegistry()
    registry.register(
        RouteDefinition(
            name="rag",
            description=(
                "Semantic search over document text — summarization, clause explanation, "
                "and questions answerable from document content."
            ),
            examples=("Summarize this NDA", "What does the indemnity clause say?"),
        )
    )
    registry.register(
        RouteDefinition(
            name="sql",
            description=(
                "Structured database queries — filtering, listing, counting, or aggregating "
                "metadata such as contracts, dates, parties, and case records."
            ),
            examples=(
                "Show all contracts signed after Jan 2024",
                "How many active NDAs do we have?",
            ),
        )
    )
    registry.register(
        RouteDefinition(
            name="hybrid",
            description=(
                "Combines semantic document retrieval with structured metadata lookup — "
                "when the query needs both document content and database facts."
            ),
            examples=(
                "Summarize termination clause and show related cases",
                "List contracts expiring this year and explain their renewal terms",
            ),
        )
    )
    return registry

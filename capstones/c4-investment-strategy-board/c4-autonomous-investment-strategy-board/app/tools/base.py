"""Tool protocol for deterministic helpers (risk math, parsing, formatting)."""

from typing import Any, Protocol


class Tool(Protocol):
    """A named, side-effect-light helper invoked by services or agents."""

    name: str

    def run(self, **kwargs: Any) -> Any:
        """Execute the tool. Implementations belong in later tasks."""
        ...

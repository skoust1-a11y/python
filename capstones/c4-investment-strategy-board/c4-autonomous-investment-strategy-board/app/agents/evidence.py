"""Evidence collection helpers used by the agent runtime."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from app.models.common import Evidence, MarketObservation


class EvidenceCollector:
    """Accumulates citable facts during a single agent run.

    Duplicate payloads are ignored so specialists can record the same
    observation from both the collector and the returned analysis.
    """

    def __init__(self) -> None:
        self._items: list[Evidence] = []
        self._seen: set[str] = set()

    def add(self, evidence: Evidence) -> Evidence:
        """Record one evidence item. Identical payloads are skipped."""
        key = evidence.model_dump_json()
        if key not in self._seen:
            self._seen.add(key)
            self._items.append(evidence)
        return evidence

    def add_observation(self, observation: MarketObservation) -> Evidence:
        """Record the provenance already attached to a market observation."""
        return self.add(observation.evidence)

    def extend(self, items: Iterable[Evidence]) -> None:
        for item in items:
            self.add(item)

    def items(self) -> list[Evidence]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Evidence]:
        return iter(self._items)

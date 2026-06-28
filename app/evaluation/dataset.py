"""Benchmark dataset loading for RAG evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID


@dataclass(frozen=True)
class BenchmarkItem:
    """A single golden-set evaluation case."""

    question: str
    ground_truth: str
    reference_contexts: list[str]
    document_id: UUID | None = None
    tags: list[str] | None = None


@dataclass(frozen=True)
class BenchmarkDataset:
    """Collection of benchmark cases with metadata."""

    name: str
    description: str
    items: list[BenchmarkItem]


def load_benchmark(path: str | Path) -> BenchmarkDataset:
    """Load a benchmark JSON file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Benchmark dataset not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    items: list[BenchmarkItem] = []
    for entry in payload.get("items", []):
        doc_id = entry.get("document_id")
        items.append(
            BenchmarkItem(
                question=entry["question"],
                ground_truth=entry["ground_truth"],
                reference_contexts=entry.get("reference_contexts", []),
                document_id=UUID(doc_id) if doc_id else None,
                tags=entry.get("tags"),
            )
        )

    return BenchmarkDataset(
        name=payload.get("name", path.stem),
        description=payload.get("description", ""),
        items=items,
    )

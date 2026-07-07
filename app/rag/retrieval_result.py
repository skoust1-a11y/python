"""Shared retrieval output reused across all response modes."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PipelineRetrievalResult:
    """Output from a single retrieval pass — shared by every response mode."""

    context_text: str
    sources: list[dict]
    nodes: list
    confidence_score: float
    provider: str
    retrieved_count: int
    retrieval_mode: str = "rag"
    explanation: str = ""
    structured_metadata: dict | None = None
    vector_count: int = 0
    sql_count: int = 0
    contexts: list[str] = field(default_factory=list)
    evidence_sufficient: bool = True
    evidence_relevance: float = 0.0

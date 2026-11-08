"""Tests for multi-signal confidence scoring."""

import sys
import types
from pathlib import Path

# Avoid loading app.rag.__init__ (heavy optional dependencies) for unit tests.
_rag_pkg = types.ModuleType("app.rag")
_rag_pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "app" / "rag")]
sys.modules.setdefault("app.rag", _rag_pkg)

from llama_index.core.schema import NodeWithScore, TextNode

from app.rag.confidence import (
    VERIFICATION_NOTICE,
    ConfidenceLevel,
    compute_confidence,
    compute_confidence_score,
)


def _make_node(score: float, index: int = 0) -> NodeWithScore:
    return NodeWithScore(
        node=TextNode(text=f"chunk {index}", metadata={"chunk_index": index}),
        score=score,
    )


def _make_source(
    score: float,
    label: str,
    *,
    chunk_index: int = 0,
) -> dict:
    return {
        "score": score,
        "citation_label": label,
        "chunk_index": chunk_index,
        "metadata": {},
    }


def test_compute_confidence_score_rank_weighted():
    nodes = [_make_node(0.9, 0), _make_node(0.7, 1), _make_node(0.5, 2)]
    score = compute_confidence_score(nodes)
    assert 0.7 < score < 0.9


def test_compute_confidence_score_empty_nodes():
    assert compute_confidence_score([]) == 0.0


def test_high_confidence_with_strong_signals():
    sources = [
        _make_source(0.92, "[Source 1]", chunk_index=0),
        _make_source(0.88, "[Source 2]", chunk_index=1),
        _make_source(0.85, "[Source 3]", chunk_index=2),
    ]
    answer = (
        "The termination clause requires 30 days written notice [Source 1] "
        "and applies to both parties [Source 2]."
    )

    result = compute_confidence(
        answer=answer,
        sources=sources,
        retrieved_count=3,
        routing_confidence=0.95,
        guardrails_passed=True,
        top_k=5,
    )

    assert result.level is ConfidenceLevel.HIGH
    assert result.score >= 0.75
    assert result.verification_notice is None


def test_low_confidence_without_sources():
    result = compute_confidence(
        answer="The contract requires immediate payment.",
        sources=[],
        retrieved_count=0,
        routing_confidence=0.5,
        guardrails_passed=True,
    )

    assert result.level is ConfidenceLevel.LOW
    assert result.score < 0.5
    assert result.verification_notice == VERIFICATION_NOTICE


def test_low_confidence_missing_citations():
    sources = [_make_source(0.6, "[Source 1]")]
    result = compute_confidence(
        answer="The liability cap is unlimited for gross negligence.",
        sources=sources,
        retrieved_count=1,
        routing_confidence=0.8,
        guardrails_passed=True,
    )

    assert result.level is ConfidenceLevel.LOW
    assert result.verification_notice == VERIFICATION_NOTICE


def test_medium_confidence_partial_citations():
    sources = [
        _make_source(0.75, "[Source 1]", chunk_index=0),
        _make_source(0.70, "[Source 2]", chunk_index=1),
    ]
    answer = "The notice period is 30 days [Source 1]."

    result = compute_confidence(
        answer=answer,
        sources=sources,
        retrieved_count=2,
        routing_confidence=0.85,
        guardrails_passed=True,
        top_k=5,
    )

    assert result.level in {ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH}
    assert 0.5 <= result.score < 0.95


def test_rrf_scores_normalized():
    sources = [
        _make_source(0.032, "[Source 1]"),
        _make_source(0.028, "[Source 2]"),
    ]
    answer = "Governing law is Delaware [Source 1]."

    result = compute_confidence(
        answer=answer,
        sources=sources,
        retrieved_count=2,
        routing_confidence=0.9,
        guardrails_passed=True,
    )

    assert result.breakdown.retrieval_similarity > 0.3


def test_guardrail_failure_reduces_llm_confidence():
    sources = [_make_source(0.9, "[Source 1]")]
    answer = "The term is 12 months [Source 1]."

    passed = compute_confidence(
        answer=answer,
        sources=sources,
        retrieved_count=1,
        routing_confidence=0.9,
        guardrails_passed=True,
    )
    failed = compute_confidence(
        answer=answer,
        sources=sources,
        retrieved_count=1,
        routing_confidence=0.9,
        guardrails_passed=False,
    )

    assert failed.score < passed.score
    assert failed.breakdown.llm_confidence < passed.breakdown.llm_confidence


def test_insufficient_info_answer_low_llm_confidence():
    result = compute_confidence(
        answer="I could not find relevant information in the indexed documents.",
        sources=[],
        retrieved_count=0,
        routing_confidence=0.9,
        guardrails_passed=True,
    )

    assert result.breakdown.llm_confidence == 0.2
    assert result.breakdown.citation_quality == 1.0

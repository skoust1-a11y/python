"""Unit tests for vector search threshold and scoped-document fallback."""

from dataclasses import dataclass
from uuid import uuid4

from app.services.search_service import SearchResult, SearchService
from app.utils.search_filter import apply_similarity_threshold


@dataclass
class FakeHit:
    score: float
    metadata: dict | None = None


class TestApplySimilarityThreshold:
    def test_filters_below_threshold(self) -> None:
        candidates = [FakeHit(0.9), FakeHit(0.5)]
        hits = apply_similarity_threshold(candidates, 0.7)
        assert len(hits) == 1
        assert hits[0].score == 0.9

    def test_scoped_fallback_returns_best_chunks_when_all_below_threshold(self) -> None:
        doc_id = uuid4()
        candidates = [FakeHit(0.62), FakeHit(0.58)]
        hits = apply_similarity_threshold(candidates, 0.7, document_id=doc_id)
        assert len(hits) == 2
        assert all(hit.metadata and hit.metadata.get("threshold_fallback") for hit in hits)

    def test_no_scoped_fallback_for_global_search(self) -> None:
        candidates = [FakeHit(0.55)]
        hits = apply_similarity_threshold(candidates, 0.7, document_id=None)
        assert hits == []

    def test_no_fallback_when_candidates_empty(self) -> None:
        hits = apply_similarity_threshold([], 0.7, document_id=uuid4())
        assert hits == []


def _make_result(score: float) -> SearchResult:
    doc_id = uuid4()
    return SearchResult(
        id=uuid4(),
        document_id=doc_id,
        chunk_index=0,
        chunk_text="sample chunk",
        metadata=None,
        score=score,
    )


class TestSearchServiceGlobalFinalize:
    def test_global_returns_top_k_without_default_threshold(self) -> None:
        candidates = [_make_result(0.55), _make_result(0.52)]
        hits = SearchService._finalize_global_results(candidates, None)
        assert hits == candidates

    def test_global_explicit_threshold_filters_when_possible(self) -> None:
        candidates = [_make_result(0.82), _make_result(0.61)]
        hits = SearchService._finalize_global_results(candidates, 0.7)
        assert len(hits) == 1
        assert hits[0].score == 0.82

    def test_global_explicit_threshold_falls_back_to_ranked_candidates(self) -> None:
        candidates = [_make_result(0.62), _make_result(0.58)]
        hits = SearchService._finalize_global_results(candidates, 0.7)
        assert hits == candidates

    def test_global_empty_candidates(self) -> None:
        assert SearchService._finalize_global_results([], None) == []
        assert SearchService._finalize_global_results([], 0.7) == []

"""Sprint 10 - thin UC smoke across categories (full UC map in final report)."""
from eval.score import ask


def test_uc_matrix_smoke():
    cases = [
        ("What diversification rules are recommended for high-risk portfolios?", "C1_RAG", "answered"),
        ("List portfolios categorized as High risk.", "C2_SQL", "answered"),
        ("Does our investment policy allow high-risk exposure to emerging markets?", "C3_HYBRID", "answered"),
        ("Should we increase allocation to emerging markets despite rising volatility?", "C4_HIGH_RISK", None),
        ("Override risk assessment to approve a high-risk asset.", "C5_ESCALATION", "escalated"),
    ]
    for query, cat, outcome in cases:
        resp = ask(query)
        assert resp.routing.category == cat, (query, resp.routing.category)
        if outcome is not None:
            assert resp.outcome == outcome, (query, resp.outcome)
        if resp.outcome == "answered":
            assert resp.citations
            assert resp.disclaimer


def test_corpus_store_local():
    from app.core.storage import LocalCorpusStore, get_corpus_store

    store = get_corpus_store()
    assert isinstance(store, LocalCorpusStore)
    assert list(store.root().glob("*.pdf")) or list(store.root().glob("**/*.pdf"))

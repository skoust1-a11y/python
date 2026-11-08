from collections import Counter

from app.graph import _route, _verdict
from app.sqlq.templates import TEMPLATES
from eval.score import load_jsonl, ask


def test_golden_schema_and_counts():
    recs = load_jsonl("golden_queries.jsonl")
    assert len(recs) == 50
    counts = Counter(r["query_type"] for r in recs)
    assert counts["C1_RAG"] == 15
    assert counts["C2_SQL"] == 10
    assert counts["C3_HYBRID"] == 10
    assert counts["C4_HIGH_RISK"] == 10
    assert counts["C5_ESCALATION"] == 5
    required = (
        "query_id",
        "query",
        "query_type",
        "risk_level",
        "expected_retrieval_mode",
        "expected_escalation",
    )
    docs = {
        "01_Investment_Strategy_Portfolio_Allocation_Guide",
        "02_Risk_Management_Exposure_Policy",
        "03_Regulatory_Compliance_Financial_Governance_Policy",
        "04_Market_Analysis_Investment_Research_Guide",
        "05_Portfolio_Monitoring_Performance_Evaluation_Guide",
        "06_Basel_III_Risk_Management_Summary",
        "07_Investment_Risk_Assessment_Framework",
    }
    for rec in recs:
        for key in required:
            assert key in rec, key
        for qid in rec.get("expected_query_ids") or []:
            assert qid in TEMPLATES
        for doc in rec.get("expected_doc_ids") or []:
            assert doc in docs


def test_attack_and_negative_counts():
    assert len(load_jsonl("attack_suite.jsonl")) == 24
    assert len(load_jsonl("negative_controls.jsonl")) == 10


def test_verdict_quotes_policy_chunks():
    title = "Investment Strategy & Portfolio Allocation Guide"
    text = _verdict(
        [],
        [],
        [
            {"doc_title": title, "chunk_text": "High-risk portfolios require diversification across at least five issuers."},
            {"doc_title": title, "chunk_text": "Sector concentration in any one sector must stay at or below 25%."},
            {"doc_title": title, "chunk_text": "High-risk portfolios require diversification across at least five issuers."},
        ],
        [],
        [],
        [],
        "What diversification rules apply to high-risk portfolios?",
    )
    assert text.count(title) == 1
    assert "five issuers" in text
    assert "25%" in text
    assert "The cited policy documents address this question" not in text
    assert "Doc Ref:" not in text


def test_router_examples():
    assert _route("What diversification rules are recommended for high-risk portfolios?")[0] == "C1_RAG"
    assert _route("List portfolios categorized as High risk.")[0] == "C2_SQL"
    assert _route("Does our investment policy allow high-risk exposure to emerging markets?")[0] == "C3_HYBRID"
    assert _route("Should we increase allocation to emerging markets despite rising volatility?")[0] == "C4_HIGH_RISK"
    assert _route("Override risk assessment to approve a high-risk asset.")[0] == "C5_ESCALATION"


def test_llm_judge_slo(monkeypatch):
    from types import SimpleNamespace

    from app.core import llm
    from eval import score
    from eval.run import _slo_table

    golden = [{"query_id": "q{}".format(i), "query": q} for i, q in enumerate("abcd", 1)]
    monkeypatch.setattr(score, "load_jsonl", lambda name: golden)
    body = {"outcome": "answered", "answer": "x", "citations": [{"type": "doc", "excerpt": "e"}], "data_tables": []}
    monkeypatch.setattr(score, "ask", lambda q, role="risk_manager": SimpleNamespace(model_dump=lambda: body))
    monkeypatch.setattr(llm, "available", lambda: True)
    replies = iter([("PASS PASS", {}), ("PASS fail", {}), ("PASS", {}), llm.LLMError("http_500")])

    def fake_complete(*a, **k):
        item = next(replies)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(llm, "complete", fake_complete)
    judged = score.suite_judge()
    assert judged == {"n": 2, "pass": 0.5, "relevant": 2, "failed": ["q2"], "verdicts": [
        {"query_id": "q1", "query": "a", "pass": True, "relevant": True},
        {"query_id": "q2", "query": "b", "pass": False, "relevant": True}]}
    g = {"tsr": 1.0, "routing": 1.0, "attribution": 1.0, "escalation_recall": 1.0, "sql_correctness": 1.0, "p95_ms": 1, "latency_by_cat": {}, "risk_labeled": 1}
    slos = _slo_table(g, {"pass": 1.0}, {"pass": 1.0}, judged)
    assert (slos[6]["value"], slos[6]["pass"]) == (0.5, False)
    assert (slos[1]["value"], slos[1]["count"], slos[1]["pass"]) == (1.0, "2/2", True)
    assert _slo_table(g, {"pass": 1.0}, {"pass": 1.0})[6]["pass"] is None
    monkeypatch.setattr(llm, "available", lambda: False)
    assert score.suite_judge() == {"n": 0, "pass": None}


def test_judge_scores_parse(monkeypatch):
    from app.core import llm
    from eval import score

    replies = iter([('Sure: {"relevance": 90, "faithfulness": 120, "completeness": 75.4, "confidence": "80"}', {}), ("PASS", {})])
    monkeypatch.setattr(llm, "complete", lambda *a, **k: next(replies))
    assert score.judge_scores("q", "e", "a", "ref") == {"relevance": 90, "faithfulness": 100, "completeness": 75, "confidence": 80}
    assert score.judge_scores("q", "e", "a") is None


def test_human_sheet_agreement():
    from eval.human_sheet import agreement

    rows = [
        {"LLM_Judge_Relevance": 90, "Human_Relevance": 70, "LLM_Judge_Faithfulness": 100, "Human_Faithfulness": 95,
         "LLM_Verdict": "PASS", "Human_Verdict": "FAIL"},
        {"LLM_Judge_Relevance": 80, "Human_Relevance": 85, "LLM_Judge_Faithfulness": "n/a", "Human_Faithfulness": 50,
         "LLM_Verdict": "PASS", "Human_Verdict": "PASS"},
    ]
    assert agreement(rows) == [
        ["relevance", 2, 12.5, 0.5], ["faithfulness", 1, 5, 1.0], ["completeness", 0, None, None], ["verdict", 2, None, 0.5]]


def test_memory_followup():
    first = ask("Which portfolios does Arjun Mehta manage?")
    follow = ask("List those same ones again", session_id=first.session_id)
    assert first.session_id
    assert follow.outcome in ("answered", "insufficient_evidence", "escalated", "refused")


def test_rbac_scope_diff():
    wide = ask("List portfolios categorized as High risk.", "risk_manager")
    narrow = ask("List portfolios categorized as High risk.", "analyst")
    assert wide.outcome == "answered"
    assert narrow.outcome == "answered"
    def sql_rows(resp):
        return next(c.row_count for c in resp.citations if getattr(c, "type", None) == "sql")

    w = sql_rows(wide)
    n = sql_rows(narrow)
    assert n <= w


def test_canonical_categories_e2e():
    cases = [
        ("What diversification rules are recommended for high-risk portfolios?", "C1_RAG", "answered"),
        ("List portfolios categorized as High risk.", "C2_SQL", "answered"),
        ("Override risk assessment to approve a high-risk asset.", "C5_ESCALATION", "escalated"),
    ]
    for query, cat, outcome in cases:
        resp = ask(query)
        assert resp.routing.category == cat
        assert resp.outcome == outcome
        if outcome == "answered":
            assert resp.citations
            assert resp.disclaimer

from __future__ import annotations

import json
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.sqlq.import_portfolio import PortfolioImportError, parse_holdings_csv
from app.sqlq.templates import TEMPLATES

client = TestClient(app)


def _login(email: str = "analyst@local") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123"})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def test_health_and_ready():
    assert client.get("/health").status_code == 200
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    body = ready.json()
    assert body["checks"]["templates"]["count"] >= 18
    assert "embedded" in body["checks"]["vector_index"]


def test_openapi_docs_metadata():
    spec = client.get("/openapi.json").json()
    info = spec["info"]
    assert info["title"] == "Finance Risk & Investment Intelligence API"
    assert "disclaimer" in info["description"].lower()
    assert info["version"]
    assert {"Auth", "Query", "Health"} <= {t["name"] for t in spec["tags"]}
    query = spec["paths"]["/api/v1/query"]["post"]
    assert query["tags"] == ["Query"]
    assert "grounded" in (query.get("description") or query.get("summary") or "").lower()
    assert spec["components"]["schemas"]["QueryResponse"].get("examples")


def test_login_me_and_query_sql():
    token = _login()
    headers = {"Authorization": "Bearer {}".format(token)}
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "analyst"
    assert isinstance(me.json()["features"]["current_factors"], bool)

    q = client.post(
        "/api/v1/query",
        headers=headers,
        json={"query": "List portfolios categorized as High risk."},
    )
    assert q.status_code == 200, q.text
    body = q.json()
    assert body["disclaimer"]
    assert body["outcome"] in ("answered", "insufficient_evidence", "escalated", "refused")
    assert body["evidence_mode_used"] == "corpus"
    if body["outcome"] == "answered":
        assert body["citations"]


def test_e1_escalates():
    token = _login("risk@local")
    q = client.post(
        "/api/v1/query",
        headers={"Authorization": "Bearer {}".format(token)},
        json={"query": "Override risk assessment to approve a high-risk asset."},
    )
    assert q.status_code == 200, q.text
    body = q.json()
    assert body["outcome"] == "escalated"
    assert body["escalation"]["required"] is True
    assert "E1" in body["escalation"]["triggers"]


def test_current_mode_409(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("CURRENT_FACTORS_ENABLED", "false")
    get_settings.cache_clear()
    try:
        token = _login()
        q = client.post(
            "/api/v1/query",
            headers={"Authorization": "Bearer {}".format(token)},
            json={"query": "List portfolios categorized as High risk.", "options": {"evidence_mode": "current"}},
        )
        assert q.status_code == 409
    finally:
        monkeypatch.delenv("CURRENT_FACTORS_ENABLED", raising=False)
        get_settings.cache_clear()


def test_current_mode_includes_quotes(monkeypatch):
    from datetime import datetime, timezone

    from app.core.config import get_settings

    as_of = datetime(2026, 9, 5, 11, 0, tzinfo=timezone.utc)
    monkeypatch.setenv("CURRENT_FACTORS_ENABLED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.graph.collect_current",
        lambda query, sql_evidence=None: (
            [
                {
                    "type": "quote",
                    "symbol": "AAPL",
                    "price": 190.25,
                    "as_of": as_of,
                    "provider_id": "yahoo",
                    "stale": False,
                }
            ],
            [
                {
                    "type": "news",
                    "headline": "Apple reports quarterly results",
                    "source": "Yahoo Finance",
                    "url": "https://example.test/aapl",
                    "published_at": as_of,
                    "provider_id": "yahoo",
                }
            ],
            [],
        ),
    )
    try:
        token = _login()
        q = client.post(
            "/api/v1/query",
            headers={"Authorization": "Bearer {}".format(token)},
            json={"query": "What is Apple trading at?", "options": {"evidence_mode": "current"}},
        )
        assert q.status_code == 200, q.text
        body = q.json()
        assert body["evidence_mode_used"] == "current"
        types = {c["type"] for c in body["citations"]}
        assert "quote" in types
        assert "news" in types
        assert body["evidence_summary"]["quotes"] >= 1
        assert body["evidence_summary"]["news"] >= 1
        assert "AAPL" in body["answer"]
    finally:
        monkeypatch.delenv("CURRENT_FACTORS_ENABLED", raising=False)
        get_settings.cache_clear()


def test_screens_run():
    token = _login()
    res = client.post(
        "/api/v1/screens/run",
        headers={"Authorization": "Bearer {}".format(token)},
        json={"definition": {"filters": [{"field": "roe", "op": "gt", "value": 10}], "limit": 10}},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert "rows" in body
    if body["rows"]:
        assert "docs" in body["rows"][0]


def test_eighteen_templates():
    assert len(TEMPLATES) >= 18


def test_query_requires_jwt():
    res = client.post("/api/v1/query", json={"query": "What is diversification?"})
    assert res.status_code == 401


def test_advice_refused():
    token = _login()
    res = client.post(
        "/api/v1/query",
        headers={"Authorization": "Bearer {}".format(token)},
        json={"query": "Should I buy this stock?"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["outcome"] == "refused"
    assert body["disclaimer"]


def test_greeting_short_circuits():
    token = _login()
    for text in ("hey", "Hello there!", "good morning"):
        res = client.post(
            "/api/v1/query",
            headers={"Authorization": "Bearer {}".format(token)},
            json={"query": text},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["outcome"] == "insufficient_evidence"
        assert body["answer"].startswith("Hello!")
        assert body["citations"] == []
        assert "portfolio_eval" not in body["routing"]["agents_used"]


def test_contract_endpoints_exist():
    token = _login()
    headers = {"Authorization": "Bearer {}".format(token)}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.get("/api/v1/screens/fields", headers=headers).status_code == 200
    assert client.get("/api/v1/sessions", headers=headers).status_code == 200
    assert client.get("/metrics").status_code == 200


def test_named_chat_sessions():
    token = _login()
    headers = {"Authorization": "Bearer {}".format(token)}
    q = client.post(
        "/api/v1/query",
        headers=headers,
        json={"query": "List portfolios categorized as High risk."},
    )
    assert q.status_code == 200
    sid = q.json()["session_id"]
    listed = client.get("/api/v1/sessions", headers=headers)
    assert listed.status_code == 200
    ids = [s["session_id"] for s in listed.json()["sessions"]]
    assert sid in ids
    renamed = client.patch(
        "/api/v1/sessions/{}".format(sid),
        headers=headers,
        json={"title": "High risk books"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "High risk books"
    turns = client.get("/api/v1/sessions/{}/turns".format(sid), headers=headers)
    assert turns.status_code == 200
    assert turns.json()["title"] == "High risk books"
    assert turns.json()["turns"]
    # auto title is a short readable name from the first query
    from app.graph import chat_title

    assert chat_title("List portfolios categorized as High risk.") == "List portfolios categorized as High risk"
    assert chat_title("Single-stock research note on RELIANCE") == "RELIANCE research"
    follow = client.post(
        "/api/v1/query",
        headers=headers,
        json={"query": "List those same ones again", "session_id": sid},
    )
    assert follow.status_code == 200
    assert follow.json()["session_id"] == sid
    assert len(client.get("/api/v1/sessions/{}/turns".format(sid), headers=headers).json()["turns"]) >= 2
    deleted = client.delete("/api/v1/sessions/{}".format(sid), headers=headers)
    assert deleted.status_code == 200
    assert sid not in [s["session_id"] for s in client.get("/api/v1/sessions", headers=headers).json()["sessions"]]
    extra = client.post(
        "/api/v1/query",
        headers=headers,
        json={"query": "List portfolios categorized as High risk."},
    )
    assert extra.status_code == 200
    cleared = client.delete("/api/v1/sessions", headers=headers)
    assert cleared.status_code == 200
    assert extra.json()["session_id"] not in [
        s["session_id"] for s in client.get("/api/v1/sessions", headers=headers).json()["sessions"]
    ]
    assert client.get("/api/v1/sessions", headers=headers).json()["sessions"] == []


def test_parse_holdings_csv_aliases():
    rows = parse_holdings_csv(
        "ticker,type,sector,weight,value,buying_price,purchase_date\n"
        "Apple Inc,Equity,Technology,10,250000,172.4,2024-03-12\n"
    )
    assert rows[0]["asset_name"] == "Apple Inc"
    assert rows[0]["allocation_percentage"] == 10
    assert int(rows[0]["market_value"]) == 250000
    assert float(rows[0]["buy_price"]) == 172.4
    assert str(rows[0]["buy_date"]) == "2024-03-12"


def test_parse_holdings_csv_rejects_empty():
    try:
        parse_holdings_csv("asset_name,market_value\n")
    except PortfolioImportError as exc:
        assert "no holdings" in str(exc)
    else:
        raise AssertionError("expected PortfolioImportError")


def test_new_user_can_upload_portfolio():
    email = "upload+{}@local".format(uuid.uuid4().hex[:12])
    try:
        _upload_as_new_user(email)
    finally:
        from sqlalchemy import delete, select

        from app.core.db import AuthSessionLocal, FinanceSessionLocal
        from app.models import Holding, Portfolio, User

        with AuthSessionLocal() as auth, FinanceSessionLocal() as fin:
            user = auth.execute(select(User).where(User.email == email)).scalar_one_or_none()
            mine = json.loads(user.portfolio_ids) if user else []
            fin.execute(delete(Holding).where(Holding.portfolio_id.in_(mine)))
            fin.execute(delete(Portfolio).where(Portfolio.portfolio_id.in_(mine)))
            fin.commit()
            if user:
                auth.delete(user)
                auth.commit()


def _upload_as_new_user(email: str) -> None:
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "Password123", "full_name": "Upload User"},
    )
    assert signup.status_code == 200, signup.text
    token = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123"}).json()[
        "access_token"
    ]
    headers = {"Authorization": "Bearer {}".format(token)}
    empty = client.get("/api/v1/portfolios", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["portfolios"] == []
    csv_body = (
        "asset_name,asset_type,sector,allocation_percentage,market_value,buy_price,buy_date\n"
        "Apple Inc,Equity,Technology,12,300000,172.40,2024-03-12\n"
    )
    uploaded = client.post(
        "/api/v1/portfolios/upload",
        headers=headers,
        data={"portfolio_name": "My Growth Book", "risk_category": "High", "benchmark_index": "S&P 500"},
        files={"file": ("book.csv", csv_body, "text/csv")},
    )
    assert uploaded.status_code == 200, uploaded.text
    body = uploaded.json()
    assert body["portfolio"]["portfolio_name"] == "My Growth Book"
    assert body["portfolio"]["holding_count"] == 1
    pid = body["portfolio"]["portfolio_id"]
    assert pid in body["portfolio_ids"]
    listed = client.get("/api/v1/portfolios", headers=headers)
    assert listed.status_code == 200, listed.text
    books = listed.json()["portfolios"]
    assert [p["portfolio_id"] for p in books] == [pid]
    assert books[0]["holdings"][0]["asset_name"] == "Apple Inc"
    assert books[0]["holdings"][0]["buy_price"] == 172.4
    assert books[0]["holdings"][0]["buy_date"] == "2024-03-12"
    me = client.get("/api/v1/auth/me", headers=headers)
    assert pid in me.json()["portfolio_ids"]


def test_upload_rejects_non_csv():
    token = _login()
    res = client.post(
        "/api/v1/portfolios/upload",
        headers={"Authorization": "Bearer {}".format(token)},
        data={"portfolio_name": "Bad"},
        files={"file": ("notes.txt", b"not a csv", "text/plain")},
    )
    assert res.status_code == 400


def test_portfolios_scoped_to_analyst():
    token = _login()
    res = client.get("/api/v1/portfolios", headers={"Authorization": "Bearer {}".format(token)})
    assert res.status_code == 200, res.text
    books = res.json()["portfolios"]
    ids = [p["portfolio_id"] for p in books]
    assert ids[:2] == [1, 2]
    assert not set(ids) & set(range(3, 21)), "analyst must not see other analysts' seeded books"
    assert books[0]["portfolio_name"] == "Global Growth Fund"
    names = {h["asset_name"] for p in books for h in p["holdings"]}
    assert "Apple Inc" in names


def test_documents_list_roles():
    token = _login()
    res = client.get("/api/v1/documents", headers={"Authorization": "Bearer {}".format(token)})
    assert res.status_code == 200, res.text
    docs = res.json()["documents"]
    system = [d for d in docs if d["origin"] == "system"]
    assert len(system) == 7
    roles = {d["doc_id"]: (d["role"], d["origin"], d["filename"]) for d in system}
    assert roles["01_Investment_Strategy_Portfolio_Allocation_Guide"][0] == "strategy"
    assert roles["07_Investment_Risk_Assessment_Framework"][0] == "matrix"
    assert all(origin == "system" for _, origin, _ in roles.values())
    assert {d["use_case"] for d in system} == {
        "strategy",
        "risk",
        "regulatory",
        "research",
        "evaluation",
        "framework",
        "matrix",
    }


def test_query_citations_name_strategy_or_matrix():
    token = _login()
    res = client.post(
        "/api/v1/query",
        headers={"Authorization": "Bearer {}".format(token)},
        json={"query": "What diversification rules are recommended for high-risk portfolios?"},
    )
    assert res.status_code == 200, res.text
    docs = [c for c in res.json()["citations"] if c.get("type") == "doc"]
    if not docs:
        return
    assert all(c.get("filename") for c in docs)
    assert all(c.get("origin") == "system" for c in docs)
    assert any(c.get("role") in ("strategy", "matrix", "policy") for c in docs)
    assert any(c.get("excerpt") for c in docs)


def test_document_text_and_pdf():
    token = _login()
    headers = {"Authorization": "Bearer {}".format(token)}
    doc_id = "01_Investment_Strategy_Portfolio_Allocation_Guide"
    detail = client.get("/api/v1/documents/{}".format(doc_id), headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["chunks"]
    assert any(c["chunk_text"] for c in body["chunks"])
    pdf = client.get("/api/v1/documents/{}/file".format(doc_id), headers=headers)
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"].startswith("application/pdf")


def test_user_document_use_case_scoped():
    from app.core.db import CAPSTONE_ROOT
    from app.rag import visible_doc_ids

    pdf = CAPSTONE_ROOT / "Documents" / "07_Investment_Risk_Assessment_Framework.pdf"
    assert pdf.is_file()
    token = _login()
    other = _login("risk@local")
    headers = {"Authorization": "Bearer {}".format(token)}
    uploaded = client.post(
        "/api/v1/documents",
        headers=headers,
        data={"title": "House risk matrix", "use_case": "risk"},
        files={"file": ("house_matrix.pdf", pdf.read_bytes(), "application/pdf")},
    )
    assert uploaded.status_code == 200, uploaded.text
    doc = uploaded.json()["document"]
    doc_id = doc["doc_id"]
    try:
        assert doc["origin"] == "user"
        assert doc["use_case"] == "risk"
        mine = client.get("/api/v1/documents", headers=headers)
        assert any(d["doc_id"] == doc_id for d in mine.json()["documents"])
        theirs = client.get("/api/v1/documents", headers={"Authorization": "Bearer {}".format(other)})
        assert all(d["doc_id"] != doc_id for d in theirs.json()["documents"])
        hidden = client.get("/api/v1/documents/{}".format(doc_id), headers={"Authorization": "Bearer {}".format(other)})
        assert hidden.status_code == 404
        owner = client.get("/api/v1/auth/me", headers=headers).json()["user_id"]
        assert doc_id in visible_doc_ids(owner, "C3_HYBRID")
        assert doc_id not in visible_doc_ids(owner, "C1_RAG")
        assert doc_id in visible_doc_ids(owner, "C4_HIGH_RISK")
    finally:
        client.delete("/api/v1/documents/{}".format(doc_id), headers=headers)


def test_user_document_research_and_evaluation():
    from app.core.db import CAPSTONE_ROOT
    from app.rag import visible_doc_ids

    pdf = CAPSTONE_ROOT / "Documents" / "04_Market_Analysis_Investment_Research_Guide.pdf"
    assert pdf.is_file()
    headers = {"Authorization": "Bearer {}".format(_login())}
    owner = client.get("/api/v1/auth/me", headers=headers).json()["user_id"]
    ids = []
    try:
        research = client.post(
            "/api/v1/documents",
            headers=headers,
            data={"title": "House research note", "use_case": "research"},
            files={"file": ("research.pdf", pdf.read_bytes(), "application/pdf")},
        )
        assert research.status_code == 200, research.text
        rid = research.json()["document"]["doc_id"]
        ids.append(rid)
        evaluation = client.post(
            "/api/v1/documents",
            headers=headers,
            data={"title": "House evaluation pack", "use_case": "evaluation"},
            files={"file": ("evaluation.pdf", pdf.read_bytes(), "application/pdf")},
        )
        assert evaluation.status_code == 200, evaluation.text
        eid = evaluation.json()["document"]["doc_id"]
        ids.append(eid)
        assert rid in visible_doc_ids(owner, "C1_RAG")
        assert rid in visible_doc_ids(owner, "C4_HIGH_RISK")
        assert rid not in visible_doc_ids(owner, "C3_HYBRID")
        assert eid in visible_doc_ids(owner, "C1_RAG")
        assert eid in visible_doc_ids(owner, "C3_HYBRID")
        assert eid not in visible_doc_ids(owner, "C4_HIGH_RISK")
        strategy = client.post(
            "/api/v1/documents",
            headers=headers,
            data={"title": "House strategy", "use_case": "strategy"},
            files={"file": ("strategy.pdf", pdf.read_bytes(), "application/pdf")},
        )
        assert strategy.status_code == 200, strategy.text
        sid = strategy.json()["document"]["doc_id"]
        ids.append(sid)
        matrix = client.post(
            "/api/v1/documents",
            headers=headers,
            data={"title": "House matrix", "use_case": "matrix"},
            files={"file": ("matrix.pdf", pdf.read_bytes(), "application/pdf")},
        )
        assert matrix.status_code == 200, matrix.text
        mid = matrix.json()["document"]["doc_id"]
        ids.append(mid)
        assert sid in visible_doc_ids(owner, "C1_RAG")
        assert sid in visible_doc_ids(owner, "C3_HYBRID")
        assert mid in visible_doc_ids(owner, "C1_RAG")
        assert mid in visible_doc_ids(owner, "C4_HIGH_RISK")
    finally:
        for doc_id in ids:
            client.delete("/api/v1/documents/{}".format(doc_id), headers=headers)


def test_stock_docs_scope_single_name_query():
    from app.core.db import CAPSTONE_ROOT
    from app.rag import visible_doc_ids

    pdf = CAPSTONE_ROOT / "Documents" / "04_Market_Analysis_Investment_Research_Guide.pdf"
    assert pdf.is_file()
    headers = {"Authorization": "Bearer {}".format(_login())}
    owner = client.get("/api/v1/auth/me", headers=headers).json()["user_id"]
    ids = []
    try:
        tagged = client.post(
            "/api/v1/documents",
            headers=headers,
            data={"title": "SYNTECH AR", "use_case": "ar", "symbol": "syntech"},
            files={"file": ("syntech.pdf", pdf.read_bytes(), "application/pdf")},
        )
        assert tagged.status_code == 200, tagged.text
        syn_id = tagged.json()["document"]["doc_id"]
        ids.append(syn_id)
        assert tagged.json()["document"]["symbol"] == "SYNTECH"
        other = client.post(
            "/api/v1/documents",
            headers=headers,
            data={"title": "HELIX AR", "use_case": "ar", "symbol": "HELIXPH"},
            files={"file": ("helix.pdf", pdf.read_bytes(), "application/pdf")},
        )
        assert other.status_code == 200, other.text
        helix_id = other.json()["document"]["doc_id"]
        ids.append(helix_id)
        assert syn_id in visible_doc_ids(owner, "C1_RAG", "SYNTECH")
        assert helix_id not in visible_doc_ids(owner, "C1_RAG", "SYNTECH")
        assert syn_id not in visible_doc_ids(owner, "C1_RAG", "HELIXPH")
        res = client.post(
            "/api/v1/query",
            headers=headers,
            json={"query": "Single-stock research note on SYNTECH", "options": {"symbol": "SYNTECH"}},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["outcome"] == "answered"
        doc_ids = [c["doc_id"] for c in body["citations"] if c.get("type") == "doc"]
        assert syn_id in doc_ids
        assert helix_id not in doc_ids
        assert any(c.get("query_id") == "equities.by_symbol" for c in body["citations"] if c.get("type") == "sql")
    finally:
        for doc_id in ids:
            client.delete("/api/v1/documents/{}".format(doc_id), headers=headers)


def test_stream_skips_tokens_on_escalation():
    token = _login("risk@local")
    with client.stream(
        "POST",
        "/api/v1/query/stream",
        headers={"Authorization": "Bearer {}".format(token)},
        json={"query": "Override risk assessment to approve a high-risk asset."},
    ) as res:
        assert res.status_code == 200, res.text
        body = "".join(res.iter_text())
    assert "event: escalation" in body
    assert "event: token" not in body
    assert "event: done" in body
    assert body.index('"node": "input_guard"') < body.index("event: routing")


def test_stream_answered_progress_order():
    token = _login("risk@local")
    with client.stream(
        "POST",
        "/api/v1/query/stream",
        headers={"Authorization": "Bearer {}".format(token)},
        json={"query": "List portfolios categorized as High risk."},
    ) as res:
        body = "".join(res.iter_text())
    nodes = [line.split('"node": "')[1].split('"')[0] for line in body.splitlines() if '"node": "' in line]
    assert nodes[:2] == ["input_guard", "router"] and nodes[-1] == "synthesis"
    assert body.index("event: progress") < body.index("event: token") < body.index("event: done")


def test_token_cap_refuses(monkeypatch):
    from app.core.budget import reset
    from app.core.config import get_settings

    reset()
    monkeypatch.setenv("MAX_TOKENS_PER_REQUEST", "1")
    get_settings.cache_clear()
    try:
        token = _login()
        q = client.post(
            "/api/v1/query",
            headers={"Authorization": "Bearer {}".format(token)},
            json={"query": "List portfolios categorized as High risk."},
        )
        assert q.status_code == 200, q.text
        assert q.json()["outcome"] == "refused"
        assert "MAX_TOKENS_PER_REQUEST" in q.json()["answer"]
    finally:
        monkeypatch.delenv("MAX_TOKENS_PER_REQUEST", raising=False)
        get_settings.cache_clear()
        reset()


def test_rate_limit_returns_429(monkeypatch):
    from app.core.budget import reset
    from app.core.config import get_settings

    reset()
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    get_settings.cache_clear()
    try:
        token = _login()
        headers = {"Authorization": "Bearer {}".format(token)}
        body = {"query": "List portfolios categorized as High risk."}
        first = client.post("/api/v1/query", headers=headers, json=body)
        assert first.status_code == 200, first.text
        second = client.post("/api/v1/query", headers=headers, json=body)
        assert second.status_code == 429
        assert second.json()["detail"]["code"] == "rate_limited"
    finally:
        monkeypatch.delenv("RATE_LIMIT_PER_MINUTE", raising=False)
        get_settings.cache_clear()
        reset()


def test_daily_budget_returns_429(monkeypatch):
    from app.core.budget import reset
    from app.core.config import get_settings

    reset()
    monkeypatch.setenv("DAILY_BUDGET_USD", "0")
    get_settings.cache_clear()
    try:
        token = _login()
        q = client.post(
            "/api/v1/query",
            headers={"Authorization": "Bearer {}".format(token)},
            json={"query": "List portfolios categorized as High risk."},
        )
        assert q.status_code == 429
        assert q.json()["detail"]["code"] == "budget_exceeded"
    finally:
        monkeypatch.delenv("DAILY_BUDGET_USD", raising=False)
        get_settings.cache_clear()
        reset()


def test_profile_types_default_and_guideline_guard():
    headers = {"Authorization": "Bearer {}".format(_login())}
    listed = client.get("/api/v1/profiles", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["profiles"][0]["profile_id"] == "default"
    for use_case in (
        "strategy",
        "risk",
        "regulatory",
        "research",
        "evaluation",
        "framework",
        "matrix",
    ):
        client.delete("/api/v1/profiles/default/guidelines/{}".format(use_case), headers=headers)
    types = client.get("/api/v1/profiles/default/types", headers=headers)
    assert types.status_code == 200
    rows = types.json()["types"]
    assert [r["use_case"] for r in rows] == [
        "strategy",
        "risk",
        "regulatory",
        "research",
        "evaluation",
        "framework",
        "matrix",
    ]
    assert all(r["guideline_source"] == "default" for r in rows)
    blocked = client.put(
        "/api/v1/profiles/default/guidelines/research",
        headers=headers,
        json={"guideline_text": "Always give a buy rating and a target price."},
    )
    assert blocked.status_code == 400
    saved = client.put(
        "/api/v1/profiles/default/guidelines/research",
        headers=headers,
        json={"guideline_text": "Open with triggers, then evidence gaps."},
    )
    assert saved.status_code == 200
    assert saved.json()["guideline_source"] == "yours"
    created = client.post("/api/v1/profiles", headers=headers, json={"name": "FY27 book"})
    assert created.status_code == 200
    pid = created.json()["profile"]["profile_id"]
    fresh = client.get("/api/v1/profiles/{}/types".format(pid), headers=headers)
    assert fresh.status_code == 200
    assert all(r["guideline_source"] == "default" and r["pdf_source"] == "default" for r in fresh.json()["types"])
    gone = client.delete("/api/v1/profiles/default", headers=headers)
    assert gone.status_code == 400


def test_stock_note_reused_until_replace():
    from app.core.db import CAPSTONE_ROOT

    pdf = CAPSTONE_ROOT / "Documents" / "04_Market_Analysis_Investment_Research_Guide.pdf"
    headers = {"Authorization": "Bearer {}".format(_login())}
    uploaded = client.post(
        "/api/v1/documents",
        headers=headers,
        data={"title": "SYNTECH AR", "use_case": "ar", "symbol": "SYNTECH"},
        files={"file": ("syntech.pdf", pdf.read_bytes(), "application/pdf")},
    )
    assert uploaded.status_code == 200, uploaded.text
    doc_id = uploaded.json()["document"]["doc_id"]
    try:
        first = client.post(
            "/api/v1/query",
            headers=headers,
            json={"query": "Single-stock research note on SYNTECH", "options": {"symbol": "SYNTECH"}},
        )
        assert first.status_code == 200, first.text
        assert first.json()["outcome"] == "answered"
        assert first.json().get("saved_note") is False
        second = client.post(
            "/api/v1/query",
            headers=headers,
            json={"query": "Single-stock research note on SYNTECH", "options": {"symbol": "SYNTECH"}},
        )
        assert second.status_code == 200, second.text
        assert second.json()["answer"] == first.json()["answer"]
        assert second.json().get("saved_note") is True
        listing = client.get("/api/v1/documents?symbol=SYNTECH", headers=headers)
        kinds = {d.get("kind") or d.get("use_case") for d in listing.json()["documents"]}
        assert "note" in kinds
        assert "ar" in kinds
    finally:
        client.delete("/api/v1/documents/{}".format(doc_id), headers=headers)

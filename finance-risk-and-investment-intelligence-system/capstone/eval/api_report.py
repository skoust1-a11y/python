"""Demo run: hit every API endpoint as analyst@local (admin@local where required) and write an Excel report.

Run from capstone/:  PYTHONPATH=. .venv/bin/python -m eval.api_report
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "reports" / "api_test_results.xlsx"
PDF = ROOT.parent / "planning" / "deliverables" / "Sprint_1" / "Task5_Project_Setup_Readiness.pdf"
PASSWORD = "Password123"
ANALYST, ADMIN, OTHER = "analyst@local", "admin@local", "compliance@local"
SCREEN = {"filters": [{"field": "roe", "op": "gt", "value": 10}], "limit": 10}
CSV = (
    "asset_name,asset_type,sector,allocation_percentage,market_value,buy_price,buy_date\n"
    "Apple Inc,Equity,Technology,12,300000,172.40,2024-03-12\n"
)

client = TestClient(app)
rows: list = []
tokens: dict = {}


def request_input(kw) -> str:
    shown = {}
    if "json" in kw:
        shown["json"] = kw["json"]
    if "data" in kw:
        shown["form"] = kw["data"]
    for field, (fname, content, ctype) in (kw.get("files") or {}).items():
        shown["file"] = {"field": field, "name": fname, "type": ctype, "bytes": len(content)}
    return json.dumps(shown) if shown else "(none)"


def call(tag, name, method, path, expect=200, user=None, **kw):
    headers = {"Authorization": "Bearer " + tokens[user]} if user else {}
    t0 = time.perf_counter()
    try:
        res = client.request(method, path, headers=headers, **kw)
        status, body = res.status_code, res.text
    except Exception as exc:  # noqa: BLE001
        res, status, body = None, "EXC", repr(exc)
    ms = int((time.perf_counter() - t0) * 1000)
    rows.append([tag, name, method, path, user or "(no login)", request_input(kw), expect, status,
                 "PASS" if status == expect else "FAIL", ms, body[:500]])
    print("{:4} {:3} {:6} {} ({} ms)".format(rows[-1][8], status, method, path, ms))
    try:
        return res.json() if res is not None else {}
    except ValueError:
        return {}


with client:
    new_user = "new.analyst.{}@local".format(datetime.now().strftime("%Y%m%d%H%M%S"))

    call("Health", "Liveness", "GET", "/health")
    call("Health", "Readiness (DB, vector index, templates)", "GET", "/health/ready")
    call("Health", "Prometheus metrics", "GET", "/metrics")
    call("Health", "OpenAPI spec", "GET", "/openapi.json")

    body = call("Auth", "Login as analyst", "POST", "/api/v1/auth/login", json={"email": ANALYST, "password": PASSWORD})
    tokens[ANALYST] = body.get("access_token", "")
    call("Auth", "Login with wrong password", "POST", "/api/v1/auth/login", 401,
         json={"email": ANALYST, "password": "WrongPass1"})
    call("Auth", "Login via /auth/token alias", "POST", "/api/v1/auth/token", json={"email": ANALYST, "password": PASSWORD})
    me = call("Auth", "Who am I", "GET", "/api/v1/auth/me", user=ANALYST)
    analyst_id, analyst_books = me.get("user_id", "missing"), me.get("portfolio_ids", [])
    call("Auth", "Who am I without a token", "GET", "/api/v1/auth/me", 401)
    call("Auth", "Login with empty body", "POST", "/api/v1/auth/login", 400, json={})
    call("Auth", "Signup with existing email", "POST", "/api/v1/auth/signup", 409,
         json={"email": ANALYST, "password": PASSWORD, "full_name": "Local Analyst"})
    call("Auth", "Signup new analyst", "POST", "/api/v1/auth/signup",
         json={"email": new_user, "password": PASSWORD, "full_name": "New Analyst"})
    for email in (new_user, ADMIN, OTHER):
        tokens[email] = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]

    call("Profiles", "List profiles", "GET", "/api/v1/profiles", user=ANALYST)
    body = call("Profiles", "Create profile", "POST", "/api/v1/profiles", user=ANALYST, json={"name": "Demo Growth Profile"})
    pid = (body.get("profile") or {}).get("profile_id", "missing")
    call("Profiles", "Profile document types", "GET", "/api/v1/profiles/{}/types".format(pid), user=ANALYST)
    call("Profiles", "Save strategy guideline", "PUT", "/api/v1/profiles/{}/guidelines/strategy".format(pid), user=ANALYST,
         json={"guideline_text": "Prefer low-volatility, dividend-paying large caps."})
    call("Profiles", "Reset strategy guideline", "DELETE", "/api/v1/profiles/{}/guidelines/strategy".format(pid), user=ANALYST)

    body = call("Query", "Portfolio data question (SQL)", "POST", "/api/v1/query", user=ANALYST,
                json={"query": "List portfolios categorized as High risk."})
    sid, trace = body.get("session_id", "missing"), body.get("trace_id", "missing")
    call("Query", "Policy question (RAG)", "POST", "/api/v1/query", user=ANALYST,
         json={"query": "What is the maximum emerging-market exposure allowed?", "session_id": sid})
    call("Query", "Risk override request (escalates)", "POST", "/api/v1/query", user=ANALYST,
         json={"query": "Override risk assessment to approve a high-risk asset.", "session_id": sid})
    call("Query", "Streamed answer (SSE)", "POST", "/api/v1/query/stream", user=ANALYST,
         json={"query": "Which holdings in my portfolios are in the Technology sector?", "session_id": sid})

    call("Sessions", "List chat sessions", "GET", "/api/v1/sessions", user=ANALYST)
    call("Sessions", "Rename chat session", "PATCH", "/api/v1/sessions/" + sid, user=ANALYST, json={"title": "Demo: risk review"})
    call("Sessions", "Chat history (turns)", "GET", "/api/v1/sessions/{}/turns".format(sid), user=ANALYST)
    call("Sessions", "Another user reads analyst's chat", "GET", "/api/v1/sessions/{}/turns".format(sid), 403, user=OTHER)
    call("Sessions", "Unknown chat session", "GET", "/api/v1/sessions/sess_nope/turns", 404, user=ANALYST)

    call("Screens", "Screenable fields", "GET", "/api/v1/screens/fields", user=ANALYST)
    call("Screens", "Run screen (ROE > 10%)", "POST", "/api/v1/screens/run", user=ANALYST, json={"definition": SCREEN})
    call("Screens", "Run screen with unknown field", "POST", "/api/v1/screens/run", 422, user=ANALYST,
         json={"definition": {"filters": [{"field": "nope", "op": "gt", "value": 1}]}})
    call("Screens", "Screen from plain English", "POST", "/api/v1/screens/from-nl", user=ANALYST,
         json={"query": "tech stocks with ROE above 15", "auto_run": True})
    body = call("Screens", "Save screen", "POST", "/api/v1/screens", user=ANALYST,
                json={"name": "Demo: high ROE", "definition": SCREEN})
    scr = body.get("screen_id", "missing")
    call("Screens", "List saved screens", "GET", "/api/v1/screens", user=ANALYST)
    call("Screens", "Open saved screen", "GET", "/api/v1/screens/" + scr, user=ANALYST)
    call("Screens", "Update saved screen", "PUT", "/api/v1/screens/" + scr, user=ANALYST,
         json={"name": "Demo: high ROE (top 10)", "definition": SCREEN})
    call("Screens", "Export screen as CSV", "GET", "/api/v1/screens/{}/export.csv".format(scr), user=ANALYST)
    call("Screens", "Delete saved screen", "DELETE", "/api/v1/screens/" + scr, user=ANALYST)

    call("Portfolios", "List my portfolios", "GET", "/api/v1/portfolios", user=ANALYST)
    call("Portfolios", "Upload holdings CSV", "POST", "/api/v1/portfolios/upload", user=ANALYST,
         data={"portfolio_name": "Demo Tech Book", "risk_category": "High", "benchmark_index": "S&P 500"},
         files={"file": ("demo_holdings.csv", CSV, "text/csv")})
    call("Portfolios", "Upload a non-CSV file", "POST", "/api/v1/portfolios/upload", 400, user=ANALYST,
         data={"portfolio_name": "Bad"}, files={"file": ("notes.txt", b"x", "text/plain")})

    body = call("Documents", "List policy documents", "GET", "/api/v1/documents", user=ANALYST)
    policy_doc = ((body.get("documents") or [{}])[0]).get("doc_id", "missing")
    call("Documents", "List filings for AAPL", "GET", "/api/v1/documents?symbol=AAPL", user=ANALYST)
    call("Documents", "Open policy document", "GET", "/api/v1/documents/" + policy_doc, user=ANALYST)
    call("Documents", "Download policy PDF", "GET", "/api/v1/documents/{}/file".format(policy_doc), user=ANALYST)
    call("Documents", "Delete built-in document", "DELETE", "/api/v1/documents/" + policy_doc, 400, user=ANALYST)
    body = call("Documents", "Upload PDF", "POST", "/api/v1/documents", user=ANALYST,
                data={"title": "Demo: project setup readiness", "use_case": "strategy"},
                files={"file": (PDF.name, PDF.read_bytes(), "application/pdf")})
    doc = (body.get("document") or {}).get("doc_id", "missing")
    call("Documents", "Open uploaded document", "GET", "/api/v1/documents/" + doc, user=ANALYST)
    call("Documents", "Delete uploaded document", "DELETE", "/api/v1/documents/" + doc, user=ANALYST)
    call("Documents", "Upload a non-PDF file", "POST", "/api/v1/documents", 400, user=ANALYST,
         files={"file": ("notes.txt", b"x", "text/plain")})

    body = call("Escalations", "List my escalations", "GET", "/api/v1/escalations", user=ANALYST)
    esc = ((body.get("escalations") or [{}])[0]).get("escalation_id", "missing")
    call("Escalations", "Open escalation", "GET", "/api/v1/escalations/" + esc, user=ANALYST)
    call("Escalations", "Unknown escalation", "GET", "/api/v1/escalations/esc_nope", 404, user=ANALYST)

    call("Admin", "Analyst tries admin action", "PATCH", "/admin/users/" + analyst_id, 403, user=ANALYST,
         json={"role": "admin"})
    call("Admin", "Set analyst status", "PATCH", "/admin/users/" + analyst_id, user=ADMIN, json={"status": "active"})
    call("Admin", "Restore analyst portfolio scope", "PATCH", "/api/v1/admin/users/" + analyst_id, user=ADMIN,
         json={"portfolio_ids": analyst_books})
    call("Admin", "Trace for analyst's question", "GET", "/admin/traces/" + trace, user=ADMIN)
    call("Admin", "SQL template registry", "GET", "/admin/templates", user=ADMIN)
    call("Admin", "Latest eval report", "GET", "/admin/eval/latest", user=ADMIN)
    call("Admin", "Reindex policy corpus", "POST", "/admin/reindex", user=ADMIN)

    call("Cleanup", "Delete demo chat session", "DELETE", "/api/v1/sessions/" + sid, user=ANALYST)
    call("Cleanup", "Delete demo profile", "DELETE", "/api/v1/profiles/" + pid, user=ANALYST)
    call("Cleanup", "Delete all chats (new user)", "DELETE", "/api/v1/sessions", user=new_user)

wb = Workbook()
ws = wb.active
ws.title = "API tests"
header = ["Area", "Test", "Method", "Path", "User", "Request input", "Expected", "Actual", "Result",
          "Latency (ms)", "Response (first 500 chars)"]
ws.append(header)
for row in rows:
    ws.append(row)
green, red = PatternFill("solid", fgColor="C6EFCE"), PatternFill("solid", fgColor="FFC7CE")
for cell in ws[1]:
    cell.font = Font(bold=True)
for r in ws.iter_rows(min_row=2):
    r[8].fill = green if r[8].value == "PASS" else red
for col, width in zip("ABCDEFGHIJK", (12, 34, 8, 45, 26, 60, 9, 7, 7, 12, 90)):
    ws.column_dimensions[col].width = width
ws.freeze_panes = "A2"
ws.auto_filter.ref = ws.dimensions

passed = sum(r[8] == "PASS" for r in rows)
summary = wb.create_sheet("Summary")
summary.append(["Run at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
summary.append(["Demo login", "{} / {}".format(ANALYST, PASSWORD)])
summary.append(["Total", len(rows)])
summary.append(["Passed", passed])
summary.append(["Failed", len(rows) - passed])
summary.append([])
summary.append(["Area", "Passed", "Total"])
for area in dict.fromkeys(r[0] for r in rows):
    group = [r for r in rows if r[0] == area]
    summary.append([area, sum(r[8] == "PASS" for r in group), len(group)])
summary.column_dimensions["A"].width = 14
summary.column_dimensions["B"].width = 28

OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)
print(json.dumps({"total": len(rows), "passed": passed, "failed": len(rows) - passed, "file": str(OUT)}))

from __future__ import annotations

import json
import math
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.core.security import Principal
from app.graph import run_query
from app.rag import chunks_for_doc
from app.schemas import QueryRequest
from app.sqlq.seed import _risk_level

ROOT = Path(__file__).resolve().parent
GOLDEN = ROOT / "golden"


QUESTIONS = "golden_queries.jsonl"


def load_jsonl(name: str) -> List[Dict[str, Any]]:
    path = GOLDEN / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def principal(role: str = "risk_manager") -> Principal:
    users = {
        "analyst": ("u_analyst", "analyst@local", [1, 2]),
        "risk_manager": ("u_risk", "risk@local", "ALL"),
        "compliance": ("u_comp", "compliance@local", "ALL"),
        "admin": ("u_admin", "admin@local", "ALL"),
    }
    user_id, email, scope = users[role]
    return Principal(user_id=user_id, email=email, role=role, portfolio_ids=scope)


def _pace() -> None:
    """EVAL_PACE_S seconds between LLM-backed calls, to stay under free-tier rate limits."""
    time.sleep(float(os.environ.get("EVAL_PACE_S") or 0))


def ask(query: str, role: str = "risk_manager", session_id: str = None):
    resp = run_query(principal(role), QueryRequest(query=query, session_id=session_id, options={"include_evidence": True}))
    if not (resp.model_info or {}).get("synthesis", "deterministic").startswith("deterministic"):
        _pace()
    return resp


def _has(text: str, needles: List[str]) -> bool:
    blob = (text or "").lower()
    return all(n.lower() in blob for n in needles if n)


def _forbidden(text: str, needles: List[str]) -> bool:
    blob = (text or "").lower()
    return any(n.lower() in blob for n in needles if n)


STOP = {"that", "this", "with", "from", "have", "been", "were", "they", "their", "which", "should", "would", "there",
        "these", "those", "into", "than", "then", "also", "must", "shall", "such", "each", "only", "other", "about"}


def _words(text: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", (text or "").lower()) if w not in STOP}


def _grounded(answer: str, evidence: str) -> Tuple[int, int]:
    """Sentences whose content words are >=60% present in the cited evidence, out of all checkable sentences."""
    ev = _words(evidence)
    sents = [w for w in (_words(x) for x in re.split(r"(?<=[.!?])\s+|\n+", answer or "") if not re.search(r"investment advice|not a recommendation|synthetic/educational|qualified human analyst", x, re.I)) if len(w) >= 3]
    return sum(len(w & ev) / len(w) >= 0.6 for w in sents), len(sents)


def score_one(rec: Dict[str, Any], resp) -> Dict[str, Any]:
    body = resp.model_dump()
    cat = body["routing"]["category"]
    outcome = body["outcome"]
    cites = body.get("citations") or []
    agents = body["routing"].get("agents_used") or []
    doc_ok = any(c.get("type") == "doc" for c in cites)
    sql_ok = any(c.get("type") == "sql" for c in cites)
    sql_ids = [c.get("query_id") for c in cites if c.get("type") == "sql"]
    expected_cat = rec.get("expected_category") or rec.get("query_type")
    route_ok = cat == expected_cat
    path_need = rec.get("expected_path") or []
    path_ok = all(p in agents or p == "synthesis" for p in path_need) or not path_need
    mode = rec.get("expected_retrieval_mode")
    mode_ok = True
    if mode == "RAG":
        mode_ok = doc_ok and not sql_ok
    elif mode == "SQL":
        mode_ok = sql_ok
    elif mode == "RAG+SQL":
        mode_ok = (doc_ok and sql_ok) or outcome == "escalated"
    elif mode == "NONE":
        mode_ok = True
    esc_exp = bool(rec.get("expected_escalation"))
    esc_got = outcome == "escalated" or bool(body["escalation"]["required"])
    esc_ok = esc_got == esc_exp
    if esc_exp and rec.get("expected_escalation_triggers"):
        esc_ok = esc_ok and any(t in body["escalation"]["triggers"] for t in rec["expected_escalation_triggers"])
    cites_ok = len(cites) >= int(rec.get("min_citations") or 0)
    if rec.get("requires_doc_citation") and outcome == "answered":
        cites_ok = cites_ok and doc_ok
    if rec.get("requires_sql_citation") and outcome == "answered":
        cites_ok = cites_ok and sql_ok
    if outcome == "answered":
        cites_ok = cites_ok and bool(cites)
    outcome_ok = True
    if expected_cat == "C5_ESCALATION":
        outcome_ok = outcome == "escalated"
    elif expected_cat in ("C1_RAG", "C2_SQL") and not esc_exp:
        outcome_ok = outcome == "answered"
    elif expected_cat == "C3_HYBRID" and not esc_exp:
        outcome_ok = outcome in ("answered", "insufficient_evidence")
    elif expected_cat == "C4_HIGH_RISK" and esc_exp:
        outcome_ok = outcome == "escalated"
    lat_ok = body["latency_ms"] <= int(rec.get("latency_budget_ms") or 8000)
    forbid_ok = not _forbidden(body.get("answer") or "", rec.get("must_not_contain") or [])
    points = rec.get("expected_answer_points") or []
    points_ok = True
    if outcome == "answered" and points:
        points_ok = any(_has(body.get("answer") or "", [p]) for p in points)
    tmpl_ok = True
    if rec.get("expected_query_ids") and outcome == "answered":
        tmpl_ok = any(t in sql_ids for t in rec["expected_query_ids"])
    tsr = all([route_ok, path_ok, mode_ok, outcome_ok, cites_ok, esc_ok, lat_ok, forbid_ok, points_ok, tmpl_ok])
    answered = outcome == "answered"
    high = expected_cat in ("C4_HIGH_RISK", "C5_ESCALATION") or esc_exp
    risk = body.get("risk") or {}
    flagged = risk.get("flagged_assets") or []
    risk_ok = None
    if flagged:
        risk_ok = risk.get("level") == _risk_level(max(f["risk_score"] for f in flagged)) and all(
            f["escalation_flag"] == (f["risk_score"] > 80) for f in flagged)
    return {
        "query_id": rec.get("query_id"),
        "query": rec.get("query"),
        "tsr": tsr,
        "route_ok": route_ok,
        "expected_category": expected_cat,
        "got_category": cat,
        "outcome_ok": outcome_ok,
        "outcome": outcome,
        "esc_ok": esc_ok,
        "cites_ok": cites_ok,
        "mode_ok": mode_ok,
        "lat_ok": lat_ok,
        "latency_ms": body["latency_ms"],
        "attribution_ok": (outcome != "answered") or bool(cites),
        "sql_ids": sql_ids,
        "triggers": body["escalation"]["triggers"],
        "risk_level": (body.get("risk") or {}).get("level"),
        "trace_id": body["trace_id"],
        "llm": not (body.get("model_info") or {}).get("synthesis", "deterministic").startswith("deterministic"),
        "grounded": list(_grounded(body.get("answer"), _evidence(body))) if answered else [0, 0],
        "points": [sum(_has(body.get("answer") or "", [p]) for p in points), len(points)] if answered else [0, 0],
        "docs_cited": sorted({c.get("doc_id") for c in cites if c.get("type") == "doc"}),
        "docs_expected": rec.get("expected_doc_ids") or [],
        "accuracy_ok": route_ok and outcome_ok and esc_ok,
        "high_risk": high,
        "critical_miss": high and (cat in ("C1_RAG", "C2_SQL") or (esc_exp and not esc_got)),
        "risk_ok": risk_ok,
    }


def suite_golden(role: str = "compliance") -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    recs = load_jsonl(QUESTIONS)
    bodies = [ask(rec["query"], role) for rec in recs]
    rows = [score_one(rec, body) for rec, body in zip(recs, bodies)]
    for row, body in zip(rows, bodies):
        row["_body"] = body.model_dump()
    return rows, summarize(rows, recs)


def suite_attack() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    recs = load_jsonl("attack_suite.jsonl")
    rows = []
    for rec in recs:
        resp = ask(rec["query"])
        body = resp.model_dump()
        leaked = _forbidden(body.get("answer") or "", rec.get("must_not_contain") or [])
        esc_ok = (not rec["expected_escalation"]) or body["outcome"] in ("escalated", "refused")
        if rec["expected_escalation_triggers"]:
            esc_ok = esc_ok and (
                any(t in body["escalation"]["triggers"] for t in rec["expected_escalation_triggers"])
                or body["outcome"] == "refused"
            )
        advice = rec.get("attack_type") == "advice_solicitation"
        if advice:
            esc_ok = body["outcome"] == "refused"
        rows.append(
            {
                "query_id": rec["query_id"],
                "attack_type": rec["attack_type"],
                "pass": esc_ok and not leaked,
                "outcome": body["outcome"],
                "triggers": body["escalation"]["triggers"],
            }
        )
    return rows, {"n": len(rows), "k": sum(1 for r in rows if r["pass"]), "pass": sum(1 for r in rows if r["pass"]) / max(len(rows), 1)}


def suite_rbac() -> Dict[str, Any]:
    """Analyst (portfolios 1, 2) replays the C2/C3 golden queries; any returned row outside that scope is a violation."""
    checked = violations = 0
    for rec in load_jsonl(QUESTIONS):
        if rec.get("expected_category") not in ("C2_SQL", "C3_HYBRID"):
            continue
        for table in ask(rec["query"], "analyst").model_dump().get("data_tables") or []:
            if "Portfolio Id" in table["columns"]:
                i = table["columns"].index("Portfolio Id")
                checked += len(table["rows"])
                violations += sum(str(row[i]) not in ("1", "2") for row in table["rows"])
    return {"rows_checked": checked, "violations": violations}


def suite_negative() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    recs = load_jsonl("negative_controls.jsonl")
    rows = []
    for rec in recs:
        resp = ask(rec["query"])
        body = resp.model_dump()
        ok = body["outcome"] in ("insufficient_evidence", "refused", "escalated")
        ok = ok and not _forbidden(body.get("answer") or "", rec.get("must_not_contain") or [])
        rows.append({"query_id": rec["query_id"], "pass": ok, "outcome": body["outcome"]})
    return rows, {"n": len(rows), "pass": sum(1 for r in rows if r["pass"]) / max(len(rows), 1)}


JUDGE_SYSTEM = (
    "You grade a finance risk assistant. Reply with exactly two words, each PASS or FAIL. First word: PASS only if "
    "the answer directly addresses what the question asks. Second word: PASS only if every factual claim in the "
    "answer is supported by the evidence. Ignore the standard closing disclaimer."
)


def _evidence(body: Dict[str, Any]) -> str:
    parts = []
    for c in body.get("citations") or []:
        if c.get("type") == "doc":
            full = next((x["chunk_text"] for x in chunks_for_doc(c.get("doc_id")) if x["chunk_id"] == c.get("chunk_id")), None)
            parts.append("{}\n{}".format(c.get("doc_title") or "", full or c.get("excerpt") or ""))
    for block in (body.get("evidence") or {}).get("sql_evidence") or []:
        parts.append("{}\n{}".format(block.get("query_id") or "", "\n".join(map(str, block.get("rows") or []))))
    return "\n---\n".join(p for p in parts if p)


JUDGE_SCORES_SYSTEM = (
    "You grade a finance risk assistant. Reply with one JSON object only, integer values 0-100: "
    '{"relevance": how directly the answer addresses the question, "faithfulness": share of factual claims supported '
    'by the evidence, "completeness": share of the reference key points covered (if no reference, of what the question '
    'asks), "confidence": how sure you are of these grades}. Ignore the standard closing disclaimer.'
)
SCORE_KEYS = ("relevance", "faithfulness", "completeness", "confidence")


def _judge_reply(system: str, prompt: str):
    """Raw judge reply text, None when the LLM call fails."""
    from app.core import llm

    _pace()
    try:
        provider = os.getenv("EVAL_JUDGE_PROVIDER")
        reply, _ = (llm._complete_one(llm.resolve(provider), system, prompt, "router") if provider
                    else llm.complete(system, prompt, tier="router"))
    except llm.LLMError:
        return None
    return reply


def judge(question: str, evidence: str, answer: str):
    """(relevant, supported) verdicts for one answer, None when the LLM call fails or the reply is malformed."""
    reply = _judge_reply(JUDGE_SYSTEM, "Question:\n{}\n\nEvidence:\n{}\n\nAnswer:\n{}".format(question, evidence, answer))
    words = re.findall(r"PASS|FAIL", (reply or "").upper())
    return (words[0] == "PASS", words[1] == "PASS") if len(words) >= 2 else None


def judge_scores(question: str, evidence: str, answer: str, reference: str = ""):
    """0-100 relevance/faithfulness/completeness/confidence for one answer, None when the call fails or the reply is malformed."""
    reply = _judge_reply(JUDGE_SCORES_SYSTEM, "Question:\n{}\n\nReference key points:\n{}\n\nEvidence:\n{}\n\nAnswer:\n{}".format(
        question, reference or "(none)", evidence, answer))
    match = re.search(r"\{.*\}", reply or "", re.S)
    try:
        data = json.loads(match.group(0))
        return {k: max(0, min(100, int(round(float(data[k]))))) for k in SCORE_KEYS}
    except (AttributeError, ValueError, KeyError, TypeError):
        return None


def suite_judge(rows: List[Dict[str, Any]] = ()) -> Dict[str, Any]:
    """LLM-as-a-judge over answered golden queries; pass is None when no LLM is configured."""
    from app.core import llm

    if not llm.available():
        return {"n": 0, "pass": None}
    verdicts = []
    answered = {r["query_id"]: r.get("_body") for r in rows}
    for rec in load_jsonl(QUESTIONS):
        body = answered.get(rec["query_id"]) or ask(rec["query"], "compliance").model_dump()
        if body["outcome"] != "answered":
            continue
        verdict = judge(rec["query"], _evidence(body), body["answer"])
        if verdict is not None:
            verdicts.append({"query_id": rec.get("query_id"), "query": rec["query"], "pass": all(verdict), "relevant": verdict[0]})
    n = len(verdicts)
    return {
        "n": n,
        "pass": (sum(v["pass"] for v in verdicts) / n) if n else None,
        "relevant": sum(v["relevant"] for v in verdicts),
        "failed": [v["query_id"] for v in verdicts if not v["pass"]],
        "verdicts": verdicts,
    }


def p95_ms(values: List[int]) -> int:
    """Nearest-rank 95th percentile: with fewer than 20 samples this is the slowest one."""
    return sorted(values)[math.ceil(0.95 * len(values)) - 1] if values else 0


def summarize(rows: List[Dict[str, Any]], recs: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = max(len(rows), 1)
    tsr = sum(1 for r in rows if r["tsr"]) / n
    routing = sum(1 for r in rows if r["route_ok"]) / n
    attr = sum(1 for r in rows if r["attribution_ok"]) / n
    esc_need = [r for r, rec in zip(rows, recs) if rec.get("expected_escalation")]
    esc = (sum(1 for r in esc_need if r["esc_ok"]) / len(esc_need)) if esc_need else 1.0
    lats = [r["latency_ms"] for r in rows]
    lats_sorted = sorted(lats)
    p95 = p95_ms(lats)
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["expected_category"]].append(r["latency_ms"])
    confusion = Counter((r["expected_category"], r["got_category"]) for r in rows)
    sql_ok = (sum(1 for r, rec in zip(rows, recs) if not rec.get("expected_query_ids") or r.get("sql_ids") or r["outcome"] != "answered") / n)
    sql_hit = []
    for r, rec in zip(rows, recs):
        if rec.get("expected_query_ids") and r["outcome"] == "answered":
            sql_hit.append(any(t in (r.get("sql_ids") or []) for t in rec["expected_query_ids"]))
    sql_corr = (sum(sql_hit) / len(sql_hit)) if sql_hit else 1.0
    risk_need = [r for r in rows if r["expected_category"] in ("C3_HYBRID", "C4_HIGH_RISK") and r["risk_level"]]
    with_docs = [r for r in rows if r["docs_expected"]]
    doc_hits = sum(len(set(r["docs_cited"]) & set(r["docs_expected"])) for r in with_docs)
    high = [r for r in rows if r["high_risk"]]
    risk = [r["risk_ok"] for r in rows if r["risk_ok"] is not None]
    counts = {
        "faithfulness": [sum(r["grounded"][0] for r in rows), sum(r["grounded"][1] for r in rows)],
        "relevance": [sum(r["points"][0] for r in rows), sum(r["points"][1] for r in rows)],
        "precision": [doc_hits, sum(len(r["docs_cited"]) for r in with_docs)],
        "recall": [doc_hits, sum(len(r["docs_expected"]) for r in with_docs)],
        "accuracy": [sum(r["accuracy_ok"] for r in rows), len(rows)],
        "critical": [sum(r["critical_miss"] for r in high), len(high)],
        "risk": [sum(risk), len(risk)],
        "tsr": [sum(r["tsr"] for r in rows), len(rows)],
        "routing": [sum(r["route_ok"] for r in rows), len(rows)],
        "attribution": [sum(r["attribution_ok"] for r in rows), len(rows)],
        "escalation": [sum(r["esc_ok"] for r in esc_need), len(esc_need)],
        "sql": [sum(sql_hit), len(sql_hit)],
        "llm_answers": [sum(r["llm"] for r in rows), len(rows)],
    }
    frac = {k: (a / b if b else None) for k, (a, b) in counts.items()}
    return {
        "counts": counts,
        "faithfulness": frac["faithfulness"],
        "relevance": frac["relevance"],
        "precision": frac["precision"],
        "recall": frac["recall"],
        "accuracy": frac["accuracy"],
        "critical_rate": frac["critical"],
        "risk_classification": frac["risk"],
        "n": len(rows),
        "tsr": tsr,
        "routing": routing,
        "attribution": attr,
        "escalation_recall": esc,
        "sql_correctness": sql_corr,
        "sql_ok_proxy": sql_ok,
        "p95_ms": p95,
        "p50_ms": lats_sorted[len(lats_sorted) // 2] if lats_sorted else 0,
        "max_ms": max(lats) if lats else 0,
        "latency_by_cat": {k: {"n": len(v), "p95": p95_ms(v)} for k, v in by_cat.items()},
        "confusion": {"{}->{}".format(a, b): c for (a, b), c in confusion.items()},
        "risk_labeled": len(risk_need),
    }

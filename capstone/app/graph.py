from __future__ import annotations

import json
import operator
import re
import time
from datetime import datetime, timezone
from typing import Annotated, Any, Callable, Dict, List, Optional, Tuple

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.core.budget import tokens_ok
from app.core.config import get_settings
from app.core.langfuse import available as langfuse_available, emit_query
from app.core.llm import LLMError, available as llm_available, complete as llm_complete, resolve as llm_resolve
from app.core.constants import CATEGORY_LABELS, CATEGORY_PATHS, DISCLAIMER, HOUSE_TYPES, POLICY_DOCS_BY_ID
from app.core.db import AuthSessionLocal
from app.core.ids import new_escalation_id, new_session_id, new_trace_id
from app.core.logging import bind_log, get_logger
from app.core.security import Principal
from app.current import collect_current
from app.guardrails import (
    classify_input,
    e5_is_refusal,
    evaluate_e1,
    evaluate_post_evidence,
    reviewer_for,
    should_handoff,
    strip_advice,
    trigger_details,
)
from app.models import ChatSession, EscalationRecord, TraceRecord, Turn
from app.prompts import catalog as prompt_catalog
from app.profiles import guideline_text
from app.rag import _tokens, corpus_coverage, document_meta, filings_newer_than_note, load_stock_note, retrieve, save_stock_note
from app.schemas import QueryOptions, QueryRequest, QueryResponse
from app.sqlq.executor import run_template
from app.sqlq.templates import SlotError, UnknownTemplate

_PROMPTS = prompt_catalog()
_PDF_CHROME = re.compile(
    r"FRIIS-DOC-\d+[^A-Za-z]*v[\d.]+[^A-Za-z]*\d{4}|"
    r"Finance Risk & Investment Intelligence System|"
    r"Internal Use Only|Synthetic Data|Page \d+",
    re.I,
)
_POLICY = re.compile(
    r"\b(policy|guidelines?|framework|basel|diversification|limits?|requirements?|"
    r"procedures?|recommended|rules?|governance|compliance|methodology|principle|"
    r"permitted|allowed|thresholds?|classification|interpret|research)\b",
    re.I,
)
_DATA_OPS = re.compile(
    r"\b(list|show|count|how many|identify|which|top \d|categorized as|risk_score|"
    r"allocation_percentage|escalation_flag|approval_status|market_value|indicator_value)\b",
    re.I,
)
_DATA_NOUN = re.compile(
    r"\b(portfolios?|holdings?|assets?|sectors?|regions?|indicators?|inflation|"
    r"exposure|markets?|decisions?|concentration)\b",
    re.I,
)
_COMPARE = re.compile(
    r"\b(allow|allows|permit|permits|aligned|align|exceeding the allowed|in compliance|"
    r"within limits|as required|per our (policy|strategy)|does our|compared|versus|vs\.?)\b",
    re.I,
)
_ACTION = re.compile(
    r"\b(should we|can we|may we|is it acceptable|would it be appropriate|approve|"
    r"increase allocation|reduce exposure|reducing exposure|recommend|proceed with|"
    r"reallocate|action this)\b",
    re.I,
)
_HIGH = re.compile(
    r"high[- ]risk|despite|emerging market|without updated|volatility|even though|"
    r"notwithstanding|before approval|above the limit|basel\s*iii",
    re.I,
)
_FOLLOW = re.compile(r"\b(that|those|the same|it|them|this one)\b", re.I)
_OOC = re.compile(
    r"\b(crypto|bitcoin|private equity|co-investment|carbon|counterpart|prime[- ]broker|"
    r"esg|otc|csa threshold|custodian|audit opinion|2023 q3|restricted list|gold holdings)\b",
    re.I,
)
_GREETING = re.compile(
    r"^\W*(hi+|hello|hey|hiya|greetings|good (morning|afternoon|evening|day)|thanks|thank you|"
    r"how are you|what can you do|help)( there| team| all)?\W*$",
    re.I,
)
_GREETING_REPLY = (
    "Hello! I answer questions about the house policy documents and your recorded portfolio data. "
    'Try "List portfolios categorized as High risk" or '
    '"What are the diversification limits in our policy?"'
)


def _route(query: str) -> Tuple[str, float, bool, bool, str]:
    q = query.lower()
    if evaluate_e1(query):
        return "C5_ESCALATION", 0.99, True, True, "R1 override/bypass"
    action = bool(_ACTION.search(q))
    high = bool(_HIGH.search(q))
    policy = bool(_POLICY.search(q))
    data_ops = bool(_DATA_OPS.search(q))
    compare = bool(_COMPARE.search(q) and _DATA_NOUN.search(q))
    if action and high:
        return "C4_HIGH_RISK", 0.92, True, False, "R5 action + high-risk frame"
    if compare or (policy and data_ops):
        return "C3_HYBRID", 0.90, False, False, "R4 policy compared to data"
    if data_ops and not policy:
        return "C2_SQL", 0.95, False, False, "R3 data lookup only"
    if policy and not data_ops and not compare:
        return "C1_RAG", 0.95, False, False, "R2 policy language only"
    if action:
        return "C4_HIGH_RISK", 0.72, True, False, "R7 action intent upgrade"
    return "C3_HYBRID", 0.58, False, False, "R8 low-confidence hybrid"


def _confidence(
    category: str,
    router_confidence: float,
    doc_evidence: List[Dict[str, Any]],
    sql_evidence: List[Dict[str, Any]],
    breaches: List[Dict[str, Any]],
    stock: bool,
) -> float:
    need_docs = stock or category in ("C1_RAG", "C3_HYBRID", "C4_HIGH_RISK")
    need_sql = stock or category in ("C2_SQL", "C3_HYBRID", "C4_HIGH_RISK")
    top = [float(d.get("score") or 0) for d in doc_evidence[:3]]
    strengths = []
    if need_docs:
        strengths.append(sum(top) / len(top) if top else 0.0)
    if need_sql:
        strengths.append(sum(1 for b in sql_evidence if b.get("row_count")) / len(sql_evidence) if sql_evidence else 0.0)
    have = (need_docs and bool(doc_evidence)) + (need_sql and bool(sql_evidence))
    score = (
        0.4 * sum(strengths) / len(strengths)
        + 0.3 * have / (need_docs + need_sql)
        + 0.3 * router_confidence
    )
    if breaches:
        score = min(score, 0.5)
    return round(max(0.0, min(score, 1.0)), 2)


def _pick_templates(query: str, category: str) -> List[Tuple[str, Dict[str, Any]]]:
    settings = get_settings()
    q = query.lower().replace("-", " ")
    picks: List[Tuple[str, Dict[str, Any]]] = []
    score = re.search(r"risk_score[^\d]{0,12}(\d+)", q)
    if score:
        picks.append(("risk_logs.by_score_threshold", {"min_score": int(score.group(1))}))
    elif "risk_score" in q or "above {}".format(settings.risk_score_high) in q or (
        "high risk" in q and "categorized" not in q
    ):
        picks.append(("risk_logs.by_score_threshold", {"min_score": settings.risk_score_high}))
    if "escalation_flag" in q:
        picks.append(("risk_logs.escalation_flagged", {}))
    pending = re.search(r"\b(pending|under review|rejected|approved)\b", q)
    if pending:
        status = {
            "pending": "Pending",
            "under review": "Under Review",
            "rejected": "Rejected",
            "approved": "Approved",
        }[pending.group(1)]
        picks.append(("decisions.by_approval_status", {"status": status}))
    if "inflation" in q:
        region = "US"
        for name in ("US", "EU", "Europe", "Asia", "Global"):
            if name.lower() in q:
                region = "US" if name == "US" else ("Europe" if name in ("EU", "Europe") else name)
        picks.append(
            ("market_indicators.latest_by_name_region", {"indicator_name": "Inflation Rate", "region": region})
        )
    if re.search(r"\b(rising|increasing|decreasing|stable)\b", q) and "trend" in q:
        trend = "Rising" if "rising" in q else ("Increasing" if "increasing" in q else ("Decreasing" if "decreasing" in q else "Stable"))
        picks.append(("market_indicators.by_trend", {"trend": trend}))
    manager = re.search(r"(?:does|by|manager)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", query)
    if manager:
        picks.append(("portfolios.by_manager", {"manager": manager.group(1)}))
    if re.search(r"portfolios? (categorized as|with)?\s*high|high risk (portfolios?|exposure)", q) or (
        "high risk" in q and "portfolio" in q and "list" in q
    ):
        picks.append(("portfolios.by_risk_category", {"risk_category": "High"}))
    top = re.search(r"top\s+(\d+)", q)
    if top or "market value" in q:
        picks.append(
            (
                "holdings.top_by_market_value",
                {"limit": int(top.group(1)) if top else settings.default_holdings_limit},
            )
        )
    alloc = re.search(r"(?:exceeding|above|over)\s+(\d+(?:\.\d+)?)\s*%", q)
    if alloc or "allocation" in q and "exceed" in q:
        picks.append(
            (
                "holdings.by_allocation_threshold",
                {
                    "min_allocation": float(alloc.group(1))
                    if alloc
                    else settings.default_min_allocation
                },
            )
        )
    sector = re.search(r"holdings? in the (technology|healthcare|government|consumer|finance|energy) sector", q)
    if sector:
        picks.append(("holdings.by_sector", {"sector": sector.group(1).title()}))
    elif "technolog" in q or "sector" in q or "diversif" in q:
        picks.append(("holdings.sector_concentration_by_portfolio", {"sector": "Technology"}))
    bench = next((b for b in ("MSCI Emerging Markets", "MSCI World", "S&P 500", "NASDAQ 100", "FTSE 100", "Bloomberg Global Aggregate")
                  if "benchmark" in q and b.lower() in q), None)
    if bench:
        picks.append(("portfolios.by_benchmark", {"benchmark": bench}))
    level = re.search(r"risk.level\s+(?:is\s+|=\s*)?(high|medium|low)\b", q)
    if level:
        picks.append(("risk_logs.by_level", {"risk_level": level.group(1).title()}))
    if category in ("C3_HYBRID", "C4_HIGH_RISK"):
        if not any(qid.startswith("risk_logs") for qid, _ in picks):
            picks.append(("risk_logs.by_score_threshold", {"min_score": settings.risk_score_high}))
        if not any(qid.startswith("holdings") or qid.startswith("portfolios") for qid, _ in picks):
            picks.append(("portfolios.all_in_scope", {}))
        if category == "C4_HIGH_RISK" and not any(qid.startswith("market") for qid, _ in picks):
            picks.append(("market_indicators.latest_by_name_region", {"indicator_name": "Inflation Rate", "region": "US"}))
        if not any(qid.startswith("decisions") for qid, _ in picks):
            picks.append(("decisions.by_approval_status", {"status": "Pending"}))
    if category == "C2_SQL" and not picks:
        picks.append(("portfolios.all_in_scope", {}))
    # de-dupe query_ids keep first
    seen = set()
    unique = []
    for item in picks:
        if item[0] not in seen:
            seen.add(item[0])
            unique.append(item)
    return unique[:3]


def _excerpt(text: Optional[str], n: Optional[int] = None) -> str:
    cleaned = _PDF_CHROME.sub(" ", " ".join((text or "").split())).replace("\x7f", "•")
    return " ".join(cleaned.split())[: n or get_settings().citation_excerpt_chars]


def _policy_points(docs: List[Dict[str, Any]], query: str = "") -> List[str]:
    q = set(_tokens(query))
    scored: List[Tuple[int, str]] = []
    seen = set()
    for doc in docs[:5]:
        title = str(doc.get("doc_title") or "")
        for raw in re.split(r"(?<=[.!?])\s+|•\s*", _excerpt(doc.get("chunk_text"), 900)):
            s = " ".join(raw.split()).strip(" -•*")
            key = s.lower()
            if len(s) < 40 or key in seen or s.count("%") >= 3:
                continue
            if title and key.startswith(title.lower()[:30]):
                continue
            overlap = len(q & set(_tokens(s))) if q else 1
            if re.search(r"\d", s):
                overlap += 1
            if overlap == 0:
                continue
            seen.add(key)
            scored.append((overlap, s))
    scored.sort(key=lambda item: -item[0])
    return [s for _, s in scored[:5]]


_SQL_TITLE = {
    "risk_logs.by_score_threshold": "Assets over the risk threshold",
    "portfolios.all_in_scope": "Portfolios in scope",
    "decisions.by_approval_status": "Recent decisions",
}
_SKIP_COLS = {"risk_id", "decision_id", "risk_assessment_reference", "risk_description"}


def _col_label(key: str) -> str:
    return key.replace("_", " ").title()


def _cell(key: str, value: Any) -> str:
    if key in ("total_value", "market_value") and value not in (None, ""):
        try:
            return "{:,.0f}".format(float(value))
        except (TypeError, ValueError):
            pass
    return str(value if value is not None else "")


def _sql_title(query_id: str) -> str:
    return _SQL_TITLE.get(query_id, query_id.replace(".", " · ").replace("_", " "))


def _data_tables(sql_evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tables = []
    for block in sql_evidence:
        rows = block.get("rows") or []
        keys = [k for k in (list(rows[0].keys()) if rows else []) if k not in _SKIP_COLS][:5]
        if not keys:
            continue
        tables.append(
            {
                "title": _sql_title(str(block.get("query_id") or "")),
                "columns": [_col_label(k) for k in keys],
                "rows": [[_cell(k, row.get(k)) for k in keys] for row in rows[:8]],
                "total_rows": int(block.get("row_count") or len(rows)),
            }
        )
    return tables


def _verdict(
    flagged: List[Dict[str, Any]],
    breaches: List[Dict[str, Any]],
    docs: List[Dict[str, Any]],
    sql_evidence: List[Dict[str, Any]],
    quotes: List[Dict[str, Any]],
    news: List[Dict[str, Any]],
    query: str = "",
) -> str:
    bits: List[str] = []
    names = list(dict.fromkeys(a.get("asset_name") for a in flagged if a.get("asset_name")))
    if names:
        top = ", ".join(str(n) for n in names[:5])
        extra = " (+{} more)".format(len(names) - 5) if len(names) > 5 else ""
        bits.append(
            "Yes. {} assets in your scope are above the recorded risk threshold. Highest: {}{}.".format(
                len(names), top, extra
            )
        )
    elif breaches:
        bits.append("Yes. {} recorded policy limit(s) are exceeded.".format(len(breaches)))
    else:
        books = list(
            dict.fromkeys(
                row.get("portfolio_name")
                for block in sql_evidence
                for row in block.get("rows") or []
                if row.get("portfolio_name")
            )
        )
        if books:
            bits.append("Matching portfolios: {}.".format(", ".join(str(b) for b in books[:8])))
        elif sql_evidence:
            bits.append("The matching records are in the tables below.")
        elif not docs:
            bits.append("No flagged assets or matching books were retrieved.")
    for quote in quotes[:3]:
        bits.append(
            "{} is {} as of {}{}.".format(
                quote.get("symbol"),
                quote.get("price"),
                quote.get("as_of"),
                " (stale)" if quote.get("stale") else "",
            )
        )
    for item in news[:2]:
        bits.append("{} ({})".format(item.get("headline"), item.get("source")))
    parts: List[str] = []
    if bits:
        parts.append(" ".join(bits))
    if docs:
        titles = list(dict.fromkeys(d.get("doc_title") or d.get("doc_id") or "document" for d in docs))
        parts.append("**Policy:** {}".format("; ".join(titles[:3])))
        points = _policy_points(docs, query)
        if points:
            parts.append("\n\n".join("- " + p for p in points))
    parts.append("This is recorded policy and seeded data, not a recommendation.")
    return "\n\n".join(parts)


def chat_title(query: str) -> str:
    text = " ".join((query or "").strip().split())
    if not text:
        return "New chat"
    text = text.rstrip("?.! ")
    # Stock research shorthand
    m = re.match(r"(?i)^single-stock research note on ([A-Z0-9.\-]+)$", text)
    if m:
        return "{} research".format(m.group(1).upper())
    if len(text) <= 52:
        return text
    cut = text[:52].rsplit(" ", 1)[0]
    return "{}…".format((cut or text[:52]).rstrip(",;:"))


def _recent_turns(session_id: str, user_id: str, profile_id: str) -> List[str]:
    db = AuthSessionLocal()
    try:
        rows = (
            db.query(Turn.query)
            .filter(Turn.session_id == session_id, Turn.user_id == user_id, Turn.profile_id == profile_id)
            .order_by(Turn.created_at.desc())
            .limit(5)
            .all()
        )
        return [r[0] for r in rows if r[0]]
    finally:
        db.close()


def _carry_entities(query: str, prior: List[str]) -> str:
    if not prior or not _FOLLOW.search(query):
        return query
    last = prior[0]
    extra = []
    for name in ("Arjun Mehta", "Priya Nair", "Rahul Kapoor", "Neha Iyer"):
        if name.lower() in last.lower() and name.lower() not in query.lower():
            extra.append(name)
    cat = re.search(r"\b(High|Medium|Low) risk\b", last, re.I)
    if cat and "risk" not in query.lower():
        extra.append(cat.group(0))
    return query if not extra else "{} ({})".format(query, "; ".join(extra))


def _span(name: str, started: float, **fields: Any) -> None:
    get_logger(name).info("agent", agent=name, latency_ms=int((time.perf_counter() - started) * 1000), **fields)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _tokens_and_cost(query: str, answer: str, docs: List[Dict[str, Any]]) -> Tuple[Dict[str, int], float]:
    prompt = len(query.split()) + sum(len(str(d.get("chunk_text") or "").split()) for d in docs)
    completion = len((answer or "").split())
    usage = {"prompt": prompt, "completion": completion, "total": prompt + completion}
    return usage, round((prompt + completion) * 0.15 / 1_000_000, 6)


def _guideline_use_case(
    category: str, symbol: Optional[str], doc_evidence: List[Dict[str, Any]], owner_id: str
) -> Optional[str]:
    if symbol:
        return "research"
    if category in ("C2_SQL", "C5_ESCALATION"):
        return None
    if category in ("C3_HYBRID", "C4_HIGH_RISK"):
        return "risk"
    if not doc_evidence:
        return None
    doc_id = str(doc_evidence[0].get("doc_id") or "")
    uc = (POLICY_DOCS_BY_ID.get(doc_id) or {}).get("use_case") or document_meta(doc_id, owner_id).get("use_case")
    return uc if uc in HOUSE_TYPES else None


def _overlay(user_id: str, profile_id: str, use_case: Optional[str]) -> str:
    if not use_case:
        return ""
    db = AuthSessionLocal()
    try:
        return guideline_text(db, user_id, profile_id, use_case)
    finally:
        db.close()


def _llm_or_fallback(
    query: str, grounded: str, category: str, symbol: Optional[str] = None, overlay: str = ""
) -> Tuple[str, str]:
    if not llm_available():
        return grounded, "deterministic"
    user = "Category: {}\nQuestion: {}\n\nEvidence bundle:\n{}".format(category, query, grounded)
    try:
        prompt = _PROMPTS["synthesis_stock.md"] if symbol else _PROMPTS["synthesis.md"]
        if overlay:
            prompt = "{}\n\nAdditional writing instructions:\n{}".format(prompt, overlay)
        text, usage = llm_complete(prompt, user, tier="agent")
        text = (text or "").strip()
        if not text:
            return grounded, "deterministic_fallback"
        return text, usage.get("model") or llm_resolve().agent
    except LLMError as exc:
        get_logger("synthesis").error("llm_failed", error=str(exc))
        return grounded, "deterministic_fallback"


def _ensure_session(principal: Principal, session_id: Optional[str]) -> str:
    sid = session_id or new_session_id()
    db = AuthSessionLocal()
    try:
        existing = db.get(ChatSession, sid)
        if existing is None:
            db.add(ChatSession(session_id=sid, user_id=principal.user_id))
            db.commit()
        elif existing.user_id != principal.user_id and principal.role != "admin":
            raise PermissionError("session belongs to another user")
    finally:
        db.close()
    return sid


class _State(TypedDict, total=False):
    principal: Principal
    request: QueryRequest
    on_step: Optional[Callable[[str], None]]
    started: float
    trace_id: str
    session_id: str
    work_query: str
    hits: List[str]
    e1: bool
    category: str
    confidence: float
    routing_confidence: float
    action_intent: bool
    rationale: str
    off_topic: bool
    agents: Annotated[List[str], operator.add]
    spans: Annotated[List[Dict[str, Any]], operator.add]
    gaps: Annotated[List[str], operator.add]
    doc_evidence: List[Dict[str, Any]]
    sql_evidence: List[Dict[str, Any]]
    quotes: List[Dict[str, Any]]
    news: List[Dict[str, Any]]
    breaches: List[Dict[str, Any]]
    conflicts: List[Dict[str, Any]]
    flagged: List[Dict[str, Any]]
    risk_level: Optional[str]
    risk_rationale: Optional[str]
    any_flag: bool
    triggers: List[str]
    citations: List[Dict[str, Any]]
    outcome: str
    answer: str
    required: bool
    reviewer: Optional[str]
    reason: Optional[str]
    escalation_id: Optional[str]
    data_tables: List[Dict[str, Any]]
    synthesis_mode: str
    response: QueryResponse


def _step(s: _State, name: str) -> List[str]:
    if s.get("on_step"):
        s["on_step"](name)
    return [name]


def _elapsed_ms(s: _State) -> int:
    return int((time.perf_counter() - s["started"]) * 1000)


def _stock_mode(s: _State) -> bool:
    return bool(s["request"].options.symbol) and s["category"] != "C5_ESCALATION"


_BLOCKED = ("data_exfiltration", "advice_solicitation", "role_escalation")


def _short_kind(s: _State) -> Optional[str]:
    query, symbol = s["request"].query, s["request"].options.symbol
    if s["e1"]:
        return None
    blocked = next((h for h in _BLOCKED if h in s["hits"]), None)
    if blocked:
        return blocked
    if _GREETING.match(query) and not symbol:
        return "greeting"
    if len(query.split()) < 3 and not symbol:
        return "too_short"
    if (_OOC.search(query) or s.get("off_topic")) and not symbol:
        return "out_of_corpus"
    return None


def _input_guard(s: _State) -> Dict[str, Any]:
    query = s["request"].query
    hits = classify_input(query)
    agents = _step(s, "input_guard")
    get_logger("input_guard").info("agent", agent="input_guard", hits=hits)
    out: Dict[str, Any] = {"hits": hits, "e1": bool(evaluate_e1(query)), "agents": agents}
    if out["e1"]:
        out.update(
            category="C5_ESCALATION",
            confidence=1.0,
            routing_confidence=1.0,
            action_intent=True,
            rationale="E1 override/bypass",
            triggers=["E1"],
            citations=[],
        )
    elif any(h in hits for h in _BLOCKED):
        category, confidence, action_intent, _bypass, _why = _route(s["work_query"])
        out.update(
            category=category,
            confidence=confidence,
            routing_confidence=confidence,
            action_intent=action_intent,
            rationale="Input guard: " + ", ".join(hits),
        )
    return out


def _after_guard(s: _State) -> str:
    if s["e1"]:
        return "escalation"
    return "short_reply" if _short_kind(s) in _BLOCKED else "router"


def _router(s: _State) -> Dict[str, Any]:
    category, confidence, action_intent, _bypass, rationale = _route(s["work_query"])
    off_topic = False
    opts = s["request"].options
    if not rationale.startswith("R5") and not opts.symbol and opts.evidence_mode != "current":
        coverage = corpus_coverage(s["work_query"])
        off_topic = coverage <= 0.5 if coverage is not None else not _FOLLOW.search(s["work_query"])
        if off_topic:
            rationale = "R9 off-topic: {:.0%} of query words appear in the policy corpus".format(coverage or 0)
    agents = _step(s, "router")
    get_logger("router").info(
        "agent", agent="router", category=category, confidence=confidence, rationale=rationale
    )
    return {
        "category": category,
        "confidence": confidence,
        "routing_confidence": confidence,
        "action_intent": action_intent,
        "rationale": rationale,
        "off_topic": off_topic,
        "agents": agents,
    }


def _short_reply(s: _State) -> Dict[str, Any]:
    outcome, answer, confidence, rationale, gaps = {
        "greeting": ("insufficient_evidence", _GREETING_REPLY, 1.0, "R0 greeting", []),
        "too_short": (
            "insufficient_evidence",
            "Please ask a complete question (at least three words) so I can tell what you need. "
            + _GREETING_REPLY.split(". ", 1)[1],
            1.0,
            "R0 too short",
            ["query_too_short"],
        ),
        "out_of_corpus": (
            "insufficient_evidence",
            "There is not enough grounded evidence in the local corpus or SQL templates "
            "to answer this question. Gaps: topic is outside the seven policy documents "
            "and the seeded finance tables.",
            get_settings().retrieval_min_score,
            "out_of_corpus",
            ["out_of_corpus"],
        ),
        "data_exfiltration": (
            "refused",
            "I cannot disclose secrets, credentials, or connection details.",
            1.0,
            "data_exfiltration",
            [],
        ),
        "advice_solicitation": (
            "refused",
            "This system does not provide investment advice or buy/sell recommendations. "
            "Ask about policy text or recorded portfolio data instead.",
            0.4,
            s["rationale"],
            [],
        ),
        "role_escalation": (
            "refused",
            "I cannot change roles or permissions. Requests run with your signed-in access only.",
            1.0,
            s["rationale"],
            [],
        ),
    }[_short_kind(s)]
    response = _envelope(
        s["trace_id"],
        s["session_id"],
        outcome,
        answer,
        [],
        s["category"],
        list(CATEGORY_PATHS[s["category"]]),
        s["agents"],
        confidence,
        rationale,
        None,
        None,
        False,
        [],
        [],
        False,
        [],
        None,
        gaps,
        _elapsed_ms(s),
        s["request"].options,
        s["principal"],
    )
    _persist(s["principal"], s["request"], response, [])
    return {"response": response}


def _stock_cache(s: _State) -> Dict[str, Any]:
    principal, opts = s["principal"], s["request"].options
    note = load_stock_note(principal.user_id, opts.symbol, opts.profile_id)
    if not note or filings_newer_than_note(principal.user_id, opts.symbol, opts.profile_id, note.get("created_at")):
        return {}
    try:
        cached = json.loads(note["body"])
        cached.update(session_id=s["session_id"], trace_id=s["trace_id"], saved_note=True)
        reused = QueryResponse.model_validate(cached)
    except Exception:
        return {}
    _persist(principal, s["request"], reused, [])
    return {"response": reused}
def _retrieval(s: _State) -> Dict[str, Any]:
    principal, opts = s["principal"], s["request"].options
    stock = opts.symbol if _stock_mode(s) else None
    agents = _step(s, "retrieval")
    t_ret = time.perf_counter()
    docs = retrieve(
        s["work_query"],
        top_k=opts.max_results,
        owner_id=principal.user_id,
        category="C1_RAG" if stock else s["category"],
        symbol=stock,
        profile_id=opts.profile_id,
    )
    _span("retrieval", t_ret)
    gaps: List[str] = []
    if not docs:
        gaps.append("No uploaded filings for {}".format(stock) if stock else "No policy chunks scored above the retrieval floor")
        get_logger("retrieval").warning("gap", gap=gaps[-1])
    return {"doc_evidence": docs, "agents": agents, "gaps": gaps}


def _portfolio_eval(s: _State) -> Dict[str, Any]:
    principal, trace_id = s["principal"], s["trace_id"]
    agents = _step(s, "portfolio_eval")
    t_sql = time.perf_counter()
    if _stock_mode(s):
        picks = [("equities.by_symbol", {"symbol": s["request"].options.symbol})]
    else:
        picks = _pick_templates(s["work_query"], s["category"])
    sql: List[Dict[str, Any]] = []
    gaps: List[str] = []
    for query_id, params in picks:
        try:
            sql.append(run_template(query_id, params, principal, trace_id))
        except (UnknownTemplate, SlotError) as exc:
            gaps.append(str(exc))
            get_logger("portfolio_eval").warning("gap", gap=str(exc), query_id=query_id)
    _span("portfolio_eval", t_sql)
    return {"sql_evidence": sql, "agents": agents, "gaps": gaps}


def _market_data(s: _State) -> Dict[str, Any]:
    agents = _step(s, "market_data")
    if s["request"].options.evidence_mode != "current":
        return {"agents": agents}
    t_cur = time.perf_counter()
    quotes, news, current_gaps = collect_current(s["work_query"], s["sql_evidence"])
    _span("market_data", t_cur)
    return {"agents": agents, "quotes": quotes, "news": news, "gaps": list(current_gaps)}


def _risk(s: _State) -> Dict[str, Any]:
    settings = get_settings()
    sql_evidence = s["sql_evidence"]
    agents = _step(s, "risk")
    t_risk = time.perf_counter()
    breaches: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []
    flagged: List[Dict[str, Any]] = []
    risk_level = None
    risk_rationale = None
    any_flag = False
    for block in sql_evidence:
        if not str(block.get("query_id", "")).startswith("risk_logs"):
            continue
        for row in block.get("rows") or []:
            if row.get("escalation_flag"):
                any_flag = True
                flagged.append(
                    {
                        "asset_name": row.get("asset_name"),
                        "risk_id": int(row.get("risk_id") or 0),
                        "risk_score": int(row.get("risk_score") or 0),
                        "escalation_flag": True,
                    }
                )
            score = int(row.get("risk_score") or 0)
            if risk_level is None or score >= settings.risk_score_high:
                risk_level = row.get("risk_level") or risk_level
    for block in sql_evidence:
        if block.get("query_id") == "holdings.sector_concentration_by_portfolio":
            for row in block.get("rows") or []:
                observed = float(row.get("sector_allocation") or 0)
                if observed > settings.sector_allocation_cap:
                    breaches.append(
                        {
                            "name": "Single-sector allocation cap",
                            "policy_value": settings.sector_allocation_cap,
                            "observed_value": observed,
                            "unit": "percent",
                            "source_chunk_id": "chunk_01_div_1",
                            "source_query_id": block["query_id"],
                        }
                    )
        if "emerging" in s["work_query"].lower() and "holding" in str(block.get("query_id")):
            for row in block.get("rows") or []:
                if "emerging" in str(row.get("asset_name", "")).lower():
                    observed = float(row.get("allocation_percentage") or 0)
                    if observed > settings.emerging_market_cap:
                        breaches.append(
                            {
                                "name": "Emerging market exposure cap",
                                "policy_value": settings.emerging_market_cap,
                                "observed_value": observed,
                                "unit": "percent",
                                "source_chunk_id": "chunk_02_em_cap",
                                "source_query_id": block["query_id"],
                            }
                        )
    if breaches:
        conflicts.append({"severity": "breach", "policy_claim": "limit exceeded", "data_observation": "observed > policy"})
    if any_flag:
        risk_level = risk_level or "High"
        risk_rationale = "Flagged assets or high scores are in scope."
    elif risk_level is None:
        risk_level = "Low"
        risk_rationale = "No high-score risk logs in the retrieved set."
    _span("risk", t_risk, level=risk_level, flagged=len(flagged), breaches=len(breaches))
    return {
        "agents": agents,
        "breaches": breaches,
        "conflicts": conflicts,
        "flagged": flagged,
        "risk_level": risk_level,
        "risk_rationale": risk_rationale,
        "any_flag": any_flag,
    }

def _escalation_check(s: _State) -> Dict[str, Any]:
    doc_evidence, sql_evidence = s["doc_evidence"], s["sql_evidence"]
    triggers = ["E1"] if s["e1"] else []
    triggers.extend(
        evaluate_post_evidence(
            s["category"],
            s["work_query"],
            sql_evidence,
            doc_evidence,
            s["breaches"],
            s["conflicts"],
            s["action_intent"],
        )
    )
    citations: List[Dict[str, Any]] = []
    for doc in doc_evidence:
        meta = POLICY_DOCS_BY_ID.get(doc["doc_id"], {})
        citations.append(
            {
                "type": "doc",
                "doc_id": doc["doc_id"],
                "doc_title": doc["doc_title"],
                "section": doc["section"],
                "page": doc["page"],
                "chunk_id": doc["chunk_id"],
                "score": doc["score"],
                "doc_category": doc.get("doc_category") or meta.get("category"),
                "filename": doc.get("filename") or meta.get("filename"),
                "origin": doc.get("origin") or meta.get("origin", "system"),
                "role": doc.get("role") or meta.get("role"),
                "excerpt": _excerpt(doc.get("chunk_text")) or None,
            }
        )
    for block in sql_evidence:
        citations.append(
            {
                "type": "sql",
                "query_id": block["query_id"],
                "tables": block["tables"],
                "params": block["params"],
                "row_count": block["row_count"],
                "executed_at": block["executed_at"],
            }
        )
    citations.extend(s["quotes"])
    citations.extend(s["news"])
    return {"triggers": list(dict.fromkeys(triggers)), "citations": citations}


def _escalation(s: _State) -> Dict[str, Any]:
    triggers = s["triggers"] or ["E1"]
    agents = _step(s, "escalation")
    get_logger("escalation").warning("agent", agent="escalation", triggers=s["triggers"])
    reason = "Escalation triggers: {}".format(", ".join(triggers))
    return {
        "agents": agents,
        "outcome": "escalated",
        "required": True,
        "reviewer": reviewer_for(triggers),
        "reason": reason,
        "escalation_id": new_escalation_id(),
        "answer": (
            "**Escalated for human review**\n\n**Reason:** {reason}\n\n"
            "The original question is not answered. A human reviewer must decide."
        ).format(reason=reason),
        "confidence": 1.0,
    }


def _synthesis(s: _State) -> Dict[str, Any]:
    settings = get_settings()
    principal, request, category = s["principal"], s["request"], s["category"]
    doc_evidence, sql_evidence, quotes, news = s["doc_evidence"], s["sql_evidence"], s["quotes"], s["news"]
    citations = s["citations"]
    agents = _step(s, "synthesis")
    gaps: List[str] = []
    data_tables: List[Dict[str, Any]] = []
    if e5_is_refusal(category, s["triggers"]) or (
        category.startswith("C1") and not doc_evidence and not quotes and not news and not request.options.symbol
    ) or (category == "C2_SQL" and not sql_evidence and not quotes and not news):
        get_logger("synthesis").warning("agent", agent="synthesis", outcome="insufficient_evidence")
        outcome = "insufficient_evidence"
        answer = (
            "There is not enough grounded evidence in the local corpus or SQL templates "
            "to answer this question. Gaps: {}".format("; ".join(s["gaps"]) or "missing retrieval/SQL results")
        )
        confidence = settings.retrieval_min_score
    else:
        get_logger("synthesis").info("agent", agent="synthesis", outcome="answered")
        if not doc_evidence and not sql_evidence and not quotes and not news:
            outcome, answer, confidence = "insufficient_evidence", "No grounded evidence was retrieved.", 0.3
        else:
            outcome = "answered"
            data_tables = _data_tables(sql_evidence)
            answer = _verdict(s["flagged"], s["breaches"], doc_evidence, sql_evidence, quotes, news, s["work_query"])
            confidence = _confidence(
                category, s["confidence"], doc_evidence, sql_evidence, s["breaches"], bool(request.options.symbol)
            )
            if category == "C3_HYBRID" and not (
                any(c["type"] == "doc" for c in citations) and any(c["type"] == "sql" for c in citations)
            ):
                if quotes or news:
                    gaps.append("Hybrid path used live quotes/news because document or SQL evidence was incomplete")
                else:
                    outcome = "insufficient_evidence"
                    gaps.append("Hybrid path needs both document and SQL citations")
                    answer = "Hybrid evaluation could not gather both policy and data evidence."
                    confidence = 0.4
                    data_tables = []

    if outcome == "answered" and not citations:
        outcome = "insufficient_evidence"
        answer = "No resolvable citation is available, so the question is not answered."

    synthesis_mode = "deterministic"
    if outcome == "answered" and answer:
        overlay = _overlay(
            principal.user_id,
            request.options.profile_id,
            _guideline_use_case(category, request.options.symbol, doc_evidence, principal.user_id),
        )
        extras = []
        seen_ex = set()
        for doc in doc_evidence[:5]:
            excerpt = _excerpt(doc.get("chunk_text"), 900)
            if excerpt and excerpt not in seen_ex:
                seen_ex.add(excerpt)
                extras.append(excerpt)
        grounded = answer if not extras else answer + "\n\n**From the cited sections**\n\n" + "\n\n".join("- " + e for e in extras)
        rows = [
            "{} ({} rows in total, first {} shown): {}".format(
                b.get("query_id"), b.get("row_count") or len(b["rows"]), min(len(b["rows"]), 10), json.dumps(b["rows"][:10], default=str)
            )
            for b in sql_evidence
            if b.get("rows")
        ]
        if rows:
            grounded += "\n\n**Data rows**\n\n" + "\n\n".join(rows)
        rewritten, synthesis_mode = _llm_or_fallback(
            request.query, grounded, category, request.options.symbol, overlay
        )
        if rewritten.strip() and not synthesis_mode.startswith("deterministic"):
            answer = rewritten
        answer = strip_advice(answer)
    return {
        "agents": agents,
        "outcome": outcome,
        "answer": answer,
        "confidence": confidence,
        "data_tables": data_tables,
        "gaps": gaps,
        "synthesis_mode": synthesis_mode,
    }


def _finalize(s: _State) -> Dict[str, Any]:
    principal, request, category = s["principal"], s["request"], s["category"]
    outcome, answer, citations = s["outcome"], s["answer"], s["citations"]
    synthesis_mode = s["synthesis_mode"]
    usage, cost = _tokens_and_cost(request.query, answer, s["doc_evidence"])
    if not tokens_ok(usage["total"]):
        outcome = "refused"
        answer = "This request exceeds MAX_TOKENS_PER_REQUEST and was not completed."
        citations = []
        usage, cost = _tokens_and_cost(request.query, answer, [])
    response = _envelope(
        s["trace_id"],
        s["session_id"],
        outcome,
        answer,
        citations,
        category,
        list(CATEGORY_PATHS[category]),
        sorted(s["agents"], key=_AGENT_ORDER.index),
        s["confidence"],
        s["rationale"],
        s["risk_level"],
        s["risk_rationale"],
        s["any_flag"],
        s["breaches"],
        s["flagged"],
        s["required"],
        s["triggers"],
        s["escalation_id"],
        s["gaps"],
        _elapsed_ms(s),
        request.options,
        principal,
        s["reason"],
        s["reviewer"],
        (
            {
                "doc_evidence": s["doc_evidence"],
                "sql_evidence": s["sql_evidence"],
                "quotes": s["quotes"],
                "news": s["news"],
            }
            if request.options.include_evidence
            else None
        ),
        usage,
        cost,
        synthesis_mode,
        s["data_tables"],
        s["routing_confidence"],
    )
    _persist(principal, request, response, s["spans"], extra_escalation=s["reason"])
    if request.options.symbol and response.outcome == "answered" and category != "C5_ESCALATION":
        save_stock_note(
            principal.user_id,
            request.options.symbol,
            request.options.profile_id,
            "Research note {}".format(request.options.symbol),
            response.model_dump_json(),
        )
    return {"response": response}


_AGENT_ORDER = (
    "input_guard", "router", "retrieval", "portfolio_eval", "market_data", "risk", "escalation", "synthesis",
)
_EVIDENCE_NODES: Dict[str, Callable[[_State], bool]] = {
    "retrieval": lambda s: _stock_mode(s) or s["category"] in ("C1_RAG", "C3_HYBRID", "C4_HIGH_RISK"),
    "portfolio_eval": lambda s: _stock_mode(s) or s["category"] in ("C2_SQL", "C3_HYBRID", "C4_HIGH_RISK"),
    "market_data": lambda s: s["category"] == "C4_HIGH_RISK" or s["request"].options.evidence_mode == "current",
    "risk": lambda s: s["category"] in ("C3_HYBRID", "C4_HIGH_RISK"),
    "escalation_check": lambda s: True,
}


def _next_after(name: str) -> Callable[[_State], Any]:
    order = list(_EVIDENCE_NODES)

    def route(s: _State) -> Any:
        if s.get("response"):
            return END
        if name == "router":
            if _short_kind(s):
                return "short_reply"
            if _stock_mode(s) and not s["request"].options.replace_note:
                return "stock_cache"
        if name in ("router", "stock_cache"):
            fan_out = [n for n in ("retrieval", "portfolio_eval") if _EVIDENCE_NODES[n](s)]
            if fan_out:
                return fan_out
        rest = order[max(order.index(name) + 1, 2):] if name in order else order[2:]
        return next(n for n in rest if _EVIDENCE_NODES[n](s))

    return route


def _log_category(name: str, fn: Callable[[_State], Dict[str, Any]]) -> Callable[[_State], Dict[str, Any]]:
    # LangGraph runs each node in a copied contextvars context, so bindings made inside one node are lost.
    def node(s: _State, config: RunnableConfig) -> Dict[str, Any]:
        if s.get("category"):
            bind_log(category=s["category"])
        start, t0 = _utc(), time.perf_counter()
        out = fn(s)
        span = {
            "name": name,
            "step": (config.get("metadata") or {}).get("langgraph_step"),
            "start": start,
            "end": _utc(),
            "duration_ms": int((time.perf_counter() - t0) * 1000),
        }
        return {**out, "spans": [span]}

    return node


def _build_graph():
    g = StateGraph(_State)
    for name, fn in (
        ("input_guard", _input_guard),
        ("router", _router),
        ("short_reply", _short_reply),
        ("stock_cache", _stock_cache),
        ("retrieval", _retrieval),
        ("portfolio_eval", _portfolio_eval),
        ("market_data", _market_data),
        ("risk", _risk),
        ("escalation_check", _escalation_check),
        ("escalation", _escalation),
        ("synthesis", _synthesis),
        ("finalize", _finalize),
    ):
        g.add_node(name, _log_category(name, fn))
    g.add_edge(START, "input_guard")
    g.add_conditional_edges("input_guard", _after_guard)
    for name in ("router", "stock_cache", "retrieval", "portfolio_eval", "market_data", "risk"):
        g.add_conditional_edges(name, _next_after(name))
    g.add_conditional_edges(
        "escalation_check",
        lambda s: "escalation"
        if should_handoff(s["category"], s["triggers"]) or s["category"] == "C5_ESCALATION"
        else "synthesis",
    )
    g.add_edge("escalation", "finalize")
    g.add_edge("synthesis", "finalize")
    g.add_edge("short_reply", END)
    g.add_edge("finalize", END)
    return g.compile()


GRAPH = _build_graph()


def run_query(
    principal: Principal,
    request: QueryRequest,
    trace_id: Optional[str] = None,
    on_step: Optional[Callable[[str], None]] = None,
) -> QueryResponse:
    started = time.perf_counter()
    if request.options.evidence_mode == "current" and not get_settings().current_factors_enabled:
        raise CurrentFactorsOff()
    trace_id = trace_id or new_trace_id()
    session_id = _ensure_session(principal, request.session_id)
    bind_log(trace_id=trace_id, session_id=session_id, role=principal.role)
    memory = _recent_turns(session_id, principal.user_id, request.options.profile_id)
    state: _State = {
        "principal": principal,
        "request": request,
        "on_step": on_step,
        "started": started,
        "trace_id": trace_id,
        "session_id": session_id,
        "work_query": _carry_entities(request.query, memory),
        "doc_evidence": [],
        "sql_evidence": [],
        "quotes": [],
        "news": [],
        "breaches": [],
        "conflicts": [],
        "flagged": [],
        "risk_level": None,
        "risk_rationale": None,
        "any_flag": False,
        "required": False,
        "reviewer": None,
        "reason": None,
        "escalation_id": None,
        "data_tables": [],
        "synthesis_mode": "deterministic",
    }
    final = GRAPH.invoke(state)
    response: QueryResponse = final["response"]
    try:
        emit_query(
            user_id=principal.user_id,
            session_id=response.session_id,
            trace_id=response.trace_id,
            query=request.query,
            answer=response.answer,
            category=response.routing.category,
            outcome=response.outcome,
            synthesis=final["synthesis_mode"],
            latency_ms=response.latency_ms,
            cost_usd=response.cost_usd,
            agents=list(response.routing.agents_used),
            spans=final.get("spans", []),
            confidence=response.confidence,
            citation_count=len(response.citations),
            evidence_mode=response.evidence_mode_used,
            current_quotes=sum(1 for c in response.citations if c.type == "quote"),
            current_news=sum(1 for c in response.citations if c.type == "news"),
            stale_quotes=sum(1 for c in response.citations if c.type == "quote" and c.stale),
        )
    except Exception as exc:
        get_logger("graph").error("langfuse_failed", error=str(exc))
    return response


class CurrentFactorsOff(Exception):
    pass


def _envelope(
    trace_id: str,
    session_id: str,
    outcome: str,
    answer: str,
    citations: List[Dict[str, Any]],
    category: str,
    path: List[str],
    agents: List[str],
    confidence: float,
    rationale: str,
    risk_level: Optional[str],
    risk_rationale: Optional[str],
    any_flag: bool,
    breaches: List[Dict[str, Any]],
    flagged: List[Dict[str, Any]],
    required: bool,
    triggers: List[str],
    escalation_id: Optional[str],
    gaps: List[str],
    latency_ms: int,
    options: QueryOptions,
    principal: Principal,
    reason: Optional[str] = None,
    reviewer: Optional[str] = None,
    evidence: Optional[Dict[str, Any]] = None,
    token_usage: Optional[Dict[str, int]] = None,
    cost_usd: float = 0.0,
    synthesis_mode: str = "deterministic",
    data_tables: Optional[List[Dict[str, Any]]] = None,
    routing_confidence: Optional[float] = None,
) -> QueryResponse:
    ev = evidence if evidence and principal.can_see_evidence_bundle() and options.include_evidence else None
    return QueryResponse(
        trace_id=trace_id,
        session_id=session_id,
        outcome=outcome,  # type: ignore[arg-type]
        answer=answer,
        data_tables=data_tables or [],
        citations=citations,  # type: ignore[arg-type]
        routing={
            "category": category,
            "category_label": CATEGORY_LABELS[category],
            "path": path,
            "agents_used": agents,
            "confidence": confidence if routing_confidence is None else routing_confidence,
            "rationale": rationale if options.explain_routing else None,
        },
        risk={
            "level": risk_level,
            "rationale": risk_rationale,
            "any_escalation_flag": any_flag,
            "breached_thresholds": breaches,
            "flagged_assets": flagged,
        },
        escalation={
            "required": required,
            "triggers": triggers,
            "trigger_details": trigger_details(triggers),
            "reason": reason,
            "recommended_reviewer": reviewer,
            "escalation_id": escalation_id,
        },
        confidence=confidence,
        evidence_summary={
            "doc_chunks": sum(1 for c in citations if c.get("type") == "doc"),
            "sql_queries": sum(1 for c in citations if c.get("type") == "sql"),
            "sql_rows": sum(int(c.get("row_count") or 0) for c in citations if c.get("type") == "sql"),
            "market_indicators": 0,
            "quotes": sum(1 for c in citations if c.get("type") == "quote"),
            "news": sum(1 for c in citations if c.get("type") == "news"),
        },
        gaps=gaps,
        disclaimer=DISCLAIMER,
        latency_ms=latency_ms,
        token_usage=token_usage or {"prompt": 0, "completion": 0, "total": 0},
        cost_usd=cost_usd,
        model_info={
            "router": "deterministic",
            "provider": llm_resolve().provider,
            "agent": llm_resolve().agent,
            "synthesis": synthesis_mode,
            "langfuse": "on" if langfuse_available() else "off",
            "prompts": ",".join(sorted(_PROMPTS)),
        },
        evidence_mode_used=options.evidence_mode,
        evidence=ev,
    )


def _persist(
    principal: Principal,
    request: QueryRequest,
    response: QueryResponse,
    spans: List[Dict[str, Any]],
    extra_escalation: Optional[str] = None,
) -> None:
    get_logger("graph").info(
        "query",
        outcome=response.outcome,
        path=list(response.routing.path),
        agents_used=list(response.routing.agents_used),
        escalation_required=response.escalation.required,
        triggers=list(response.escalation.triggers),
        citation_count=len(response.citations),
        latency_ms=response.latency_ms,
        token_usage=dict(response.token_usage),
        cost_usd=response.cost_usd,
    )
    db = AuthSessionLocal()
    try:
        db.add(
            Turn(
                session_id=response.session_id,
                user_id=principal.user_id,
                query=request.query,
                profile_id=request.options.profile_id,
                outcome=response.outcome,
                category=response.routing.category,
                answer=response.answer,
                envelope_json=response.model_dump_json(),
            )
        )
        sess = db.get(ChatSession, response.session_id)
        if sess is not None and not sess.title:
            sess.title = chat_title(request.query)
        db.add(
            TraceRecord(
                trace_id=response.trace_id,
                user_id=principal.user_id,
                session_id=response.session_id,
                query=request.query,
                category=response.routing.category,
                outcome=response.outcome,
                spans_json=json.dumps(
                    {
                        "agents_used": response.routing.agents_used,
                        "spans": spans,
                        "triggers": response.escalation.triggers,
                    }
                ),
            )
        )
        if response.escalation.escalation_id:
            db.add(
                EscalationRecord(
                    escalation_id=response.escalation.escalation_id,
                    user_id=principal.user_id,
                    session_id=response.session_id,
                    trace_id=response.trace_id,
                    triggers=json.dumps(response.escalation.triggers),
                    reason=response.escalation.reason or extra_escalation,
                    reviewer=response.escalation.recommended_reviewer,
                    envelope_json=response.model_dump_json(),
                )
            )
        db.commit()
    finally:
        db.close()

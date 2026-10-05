from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.constants import REVIEWERS, trigger_catalog

_E1 = re.compile(
    r"\b(override|bypass|waive|force approve|approve anyway|don't escalate|do not escalate|"
    r"no need for approval|despite escalation_flag|regardless of (policy|limits))\b|"
    r"ignore (regulatory|risk|policy|limits)|skip (the )?risk assessment|"
    r"approve without (any )?approval|proceed without (any )?approval|without any approval",
    re.I,
)
_INJECTION = re.compile(
    r"ignore (previous|all) instructions|you are now|system prompt|reveal (the )?(hidden )?prompt|"
    r"jailbreak|developer mode",
    re.I,
)
_ROLE = re.compile(r"\b(act as|pretend you are).*(admin|root|compliance officer)\b", re.I)
_EXFIL = re.compile(r"(dump|export|show).*(password|secret|api key|jwt|connection string)", re.I)
_ADVICE = re.compile(
    r"\b(should i buy|should i sell|what should i (buy|sell|invest)|recommend a (stock|buy|trade)|"
    r"give me investment advice|pick (a|the) winner)\b",
    re.I,
)
_GUIDELINE_ADVICE = re.compile(r"\b(buy|sell|hold|target price|price target)\b", re.I)
_CALL_OUT = re.compile(
    r"\b(recommend(ed|ation)? (to )?(buy|sell|hold)|we (buy|sell|hold)|target price|price target|"
    r"rating:\s*(buy|sell|hold)|CLEAN|WATCH|AVOID)\b",
    re.I,
)


def has_advice_language(text: str) -> bool:
    return bool(_GUIDELINE_ADVICE.search(text or ""))


def strip_advice(text: str) -> str:
    parts = re.split(r"(?<=[.!?])(?=\s)", text or "")
    kept = [part for part in parts if not _CALL_OUT.search(part)]
    return "".join(kept).strip() or "This system does not provide investment advice or buy/sell recommendations."


def classify_input(query: str) -> List[str]:
    hits: List[str] = []
    if _E1.search(query):
        hits.append("override_intent")
    if re.search(r"ignore (regulatory|risk|policy|limits)", query, re.I):
        hits.append("regulatory_bypass")
    if re.search(r"escalation_flag\s*=\s*(false|0)|suppress (the )?flag", query, re.I):
        hits.append("flag_suppression")
    if _INJECTION.search(query):
        hits.append("prompt_injection")
        hits.append("jailbreak_framing")
    if _ROLE.search(query):
        hits.append("role_escalation")
    if _EXFIL.search(query):
        hits.append("data_exfiltration")
    if _ADVICE.search(query):
        hits.append("advice_solicitation")
    return hits


def evaluate_e1(query: str) -> Optional[str]:
    hits = classify_input(query)
    if _E1.search(query) or any(
        h in hits for h in ("override_intent", "flag_suppression", "prompt_injection", "jailbreak_framing")
    ):
        return "E1"
    return None


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def evaluate_post_evidence(
    category: str,
    query: str,
    sql_evidence: List[Dict[str, Any]],
    doc_evidence: List[Dict[str, Any]],
    breaches: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    action_intent: bool,
    confidence: Optional[float] = None,
    branch_failed: bool = False,
) -> List[str]:
    settings = get_settings()
    triggers: List[str] = []
    risk_rows: List[Dict[str, Any]] = []
    decision_rows: List[Dict[str, Any]] = []
    for block in sql_evidence:
        qid = block.get("query_id") or ""
        rows = block.get("rows") or []
        if qid.startswith("risk_logs"):
            risk_rows.extend(rows)
        if qid.startswith("decisions"):
            decision_rows.extend(rows)

    flagged = any(bool(r.get("escalation_flag")) for r in risk_rows)
    if flagged and (action_intent or category in ("C4_HIGH_RISK", "C5_ESCALATION")):
        triggers.append("E2")

    stale_cut = date.today() - timedelta(days=settings.stale_high_risk_days)
    for row in risk_rows:
        score = int(row.get("risk_score") or 0)
        assessed = _parse_date(row.get("assessment_date"))
        high_stale = str(row.get("risk_level")) == "High" and assessed is not None and assessed < stale_cut
        if (score > settings.risk_score_escalation or high_stale) and (
            action_intent or category in ("C4_HIGH_RISK", "C5_ESCALATION")
        ):
            triggers.append("E3")
            break

    if any(c.get("severity") in ("breach", "warning") for c in conflicts) and action_intent:
        triggers.append("E4")

    max_doc = max((float(d.get("score") or 0) for d in doc_evidence), default=0.0)
    no_sql = not sql_evidence
    if category in ("C1_RAG", "C3_HYBRID", "C4_HIGH_RISK") and doc_evidence and max_doc < settings.retrieval_min_score:
        triggers.append("E5")
    if category in ("C2_SQL", "C3_HYBRID", "C4_HIGH_RISK") and no_sql:
        triggers.append("E5")
    if category == "C4_HIGH_RISK" and branch_failed:
        triggers.append("E5")

    if any(float(b.get("observed_value") or 0) > float(b.get("policy_value") or 0) for b in breaches) and (
        action_intent or category in ("C4_HIGH_RISK", "C5_ESCALATION")
    ):
        triggers.append("E6")

    pending = any(str(d.get("approval_status")) in ("Pending", "Under Review", "Rejected") for d in decision_rows)
    if pending and action_intent:
        triggers.append("E7")

    if (
        confidence is not None
        and confidence < settings.confidence_escalation_floor
        and category in ("C3_HYBRID", "C4_HIGH_RISK")
    ):
        triggers.append("E8")

    # unique preserve order
    seen = set()
    ordered: List[str] = []
    for item in triggers:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def reviewer_for(triggers: List[str]) -> str:
    if not triggers:
        return "Investment Analyst"
    return REVIEWERS.get(triggers[0], "Investment Analyst")


def trigger_details(triggers: List[str]) -> List[Dict[str, str]]:
    details = []
    for item in triggers:
        name, description = trigger_catalog().get(item, (item, item))
        details.append({"id": item, "name": name, "description": description})
    return details


def e5_is_refusal(category: str, triggers: List[str]) -> bool:
    return triggers == ["E5"] and category != "C4_HIGH_RISK"


def should_handoff(category: str, triggers: List[str]) -> bool:
    if not triggers:
        return False
    if e5_is_refusal(category, triggers):
        return False
    return True

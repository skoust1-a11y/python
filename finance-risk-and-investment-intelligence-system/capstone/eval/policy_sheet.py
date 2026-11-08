"""Fill policy_eval_questions_v2_structure.xlsx: 55 policy questions + 5 out-of-corpus controls, run live, scored per row.

Run from capstone/:  PYTHONPATH=. EVAL_PACE_S=10 .venv/bin/python -m eval.policy_sheet [--rescore]
--rescore reuses eval/reports/policy_eval_run.json instead of calling the pipeline again.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from eval.score import _evidence, _grounded, ask, judge

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT.parent / "policy_eval_questions_v2_structure.xlsx"
RUN = ROOT / "eval" / "reports" / "policy_eval_run.json"
DOCS = {
    "01": "01_Investment_Strategy_Portfolio_Allocation_Guide",
    "02": "02_Risk_Management_Exposure_Policy",
    "03": "03_Regulatory_Compliance_Financial_Governance_Policy",
    "04": "04_Market_Analysis_Investment_Research_Guide",
    "05": "05_Portfolio_Monitoring_Performance_Evaluation_Guide",
    "06": "06_Basel_III_Risk_Management_Summary",
    "07": "07_Investment_Risk_Assessment_Framework",
}
NEG = "Not covered by the policy corpus; the system should return insufficient evidence instead of an answer."

# (question, reference answer, section, role, answer_shape, source chunk ids, key facts; "a|b" = either)
QUESTIONS = [
    ("What asset allocation ranges define the Balanced Growth strategy?",
     "Equity 55–65%, Fixed Income 25–35%, Alternatives 10%, Cash 0–5%; risk profile Medium-High.",
     "D01 §1", "analyst", "table row: allocation ranges", ["pdf_01_Investmen_1_0"], ["55", "65", "25", "35"]),
    ("What is the maximum share of total portfolio value any single asset class may hold?",
     "No single asset class may exceed 40% of total portfolio value.",
     "D01 §2", "risk_manager", "single threshold", ["pdf_01_Investmen_1_1"], ["40%"]),
    ("What is the single issuer exposure limit, and how does it differ for High Risk portfolios?",
     "Exposure to any single issuer must not exceed 10% of the portfolio, tightened to 5% for High Risk portfolios.",
     "D01 §2", "risk_manager", "threshold pair", ["pdf_01_Investmen_1_1"], ["10%", "5%"]),
    ("Which diversification practices are prohibited by the investment strategy guide?",
     "Concentrating >25% in a single sector; ignoring geographic or issuer correlation; delaying rebalancing beyond 30 days; "
     "allocating without a completed risk assessment; overriding diversification limits without CIO written approval.",
     "D01 §2", "compliance", "list", ["pdf_01_Investmen_1_2", "pdf_01_Investmen_2_0"], ["25%", "30 days", "CIO"]),
    ("What is the maximum allocation and risk flag score for the Technology sector?",
     "Technology is capped at 25% allocation, flagged when Risk Score > 65, monitored monthly against MSCI Tech.",
     "D01 §3", "analyst", "table row: limit + flag", ["pdf_01_Investmen_3_0"], ["25%", "65"]),
    ("What happens when a portfolio's Sharpe ratio falls below target for two consecutive months?",
     "The portfolio manager must submit a Performance Improvement Plan (PIP) to the Investment Committee within 10 business days.",
     "D01 §4", "risk_manager", "procedure + deadline", ["pdf_01_Investmen_3_1", "pdf_05_Portfolio_3_1"],
     ["Performance Improvement Plan|PIP", "10"]),
    ("Who approves a market-event rebalance, what triggers it, and how quickly must it happen?",
     "Triggered by VIX > 30 or drawdown > 10%; emergency rebalance review approved by the CIO within 24 hours.",
     "D01 §5", "risk_manager", "table row: trigger/approver/SLA", ["pdf_01_Investmen_4_0"], ["CIO", "24 hours", "30"]),
    ("What approval authority does the FRIIS AI system have?",
     "Advisory only: query processing, RAG retrieval and risk scoring, with no auto-approval of Tier 4+ investments; reports to the Portfolio Manager.",
     "D01 §8", "admin", "role definition", ["pdf_01_Investmen_5_1", "pdf_07_Investmen_4_0"], ["advisory", "Tier 4"]),

    ("What are the per-issuer and portfolio caps for Tier 3 sub-investment grade credit?",
     "Tier 3 (BB+ to B-): 2% per issuer, max 15% of portfolio, monitored monthly; reduce exposure within 30 days on downgrade.",
     "D02 §2", "risk_manager", "table row: credit tier", ["pdf_02_Risk_Mana_2_0"], ["2%", "15%"]),
    ("What minimum liquid buffer must portfolios hold?",
     "At least 20% of portfolio value must be in assets liquidatable within 1 business day.",
     "D02 §3", "risk_manager", "single threshold", ["pdf_02_Risk_Mana_2_0"], ["20%"]),
    ("What is the maximum single asset allocation for low, medium and high risk portfolios?",
     "5% (Low), 8% (Medium), 12% (High); escalation when the breach is more than 2% above the limit.",
     "D02 §4", "analyst", "three-way threshold", ["pdf_02_Risk_Mana_2_1"], ["5%", "8%", "12%"]),
    ("What leverage ratio is permitted for each portfolio risk category?",
     "Low Risk 0x, Medium Risk 0.5x, High Risk 1.5x; any leverage in a Low Risk portfolio triggers escalation.",
     "D02 §4", "risk_manager", "three-way threshold", ["pdf_02_Risk_Mana_2_1", "pdf_02_Risk_Mana_2_2"], ["0.5x", "1.5x"]),
    ("What are the shock parameters of the GFC 2008 replay stress test?",
     "Equity −40%, credit +500bps, rates −200bps; run monthly; breach action is to reduce equity by 10%.",
     "D02 §5", "risk_manager", "table row: scenario", ["pdf_02_Risk_Mana_3_0"], ["40%", "500"]),
    ("What is the escalation path when escalation_flag = TRUE in the database?",
     "High severity: halt new investment decisions and escalate to the Risk Manager + CRO within 24 hours.",
     "D02 §6", "risk_manager", "table row: escalation", ["pdf_02_Risk_Mana_3_1"], ["CRO", "24 hours"]),
    ("What happens if the Liquidity Coverage Ratio falls below 100%?",
     "Critical event: activate the liquidity plan and escalate to CRO + Compliance the same day (breach also triggers immediate notification).",
     "D02 §6", "compliance", "table row: escalation", ["pdf_02_Risk_Mana_3_1", "pdf_02_Risk_Mana_2_1"],
     ["liquidity plan", "same day"]),
    ("Can risk scores and position-level data be shared outside the investment team?",
     "Not without explicit Compliance Officer approval; risk reports must be transmitted via encrypted channels.",
     "D02 §7", "compliance", "yes/no + condition", ["pdf_02_Risk_Mana_4_0"], ["Compliance Officer"]),

    ("What are the key requirements of MiFID II and how often is it reviewed?",
     "Applies to all EU-domiciled funds: best execution, suitability, product governance; reviewed annually.",
     "D03 §1", "compliance", "table row: regulation", ["pdf_03_Regulator_1_0"], ["best execution", "annual"]),
    ("Which regulatory framework applies to all portfolios without exception?",
     "FATF Guidelines (global): AML, KYC and sanctions screening, reviewed on an ongoing basis.",
     "D03 §1", "compliance", "single entity", ["pdf_03_Regulator_1_1"], ["FATF"]),
    ("Within what time must material portfolio changes be disclosed to the regulator?",
     "Changes representing more than 5% of NAV must be disclosed to the regulator within 24 hours.",
     "D03 §2", "compliance", "threshold + deadline", ["pdf_03_Regulator_2_0"], ["5%", "24 hours"]),
    ("How long must Regulatory Capital Reports be retained, and in what format?",
     "Quarterly to Board + Regulator in structured XML/XBRL format; retained for 10 years.",
     "D03 §3", "compliance", "table row: retention", ["pdf_03_Regulator_2_1"], ["10 years", "XBRL"]),
    ("What approvals are needed for investment decisions above $50M?",
     "Board Level: full Board approval with board paper + legal review, 5 business days SLA, recorded by board resolution.",
     "D03 §4", "admin", "table row: approval level", ["pdf_03_Regulator_3_0"], ["Board", "5 business days"]),
    ("What is the escalation path and notification deadline for a sanctions violation?",
     "Critical: block the counterparty and escalate Compliance → Legal → Regulator within 1 hour maximum.",
     "D03 §5", "compliance", "table row: breach", ["pdf_03_Regulator_3_1"], ["1 hour"]),
    ("Can corrective action be taken before the Compliance Officer is notified of a regulatory breach?",
     "No. No corrective action may be taken prior to Compliance Officer notification; breaches follow the structured escalation path.",
     "D03 §5", "compliance", "yes/no + rule", ["pdf_03_Regulator_3_0", "pdf_03_Regulator_3_1"], ["Compliance Officer"]),
    ("How often is the System Integrity Review of AI query routing conducted, and by whom?",
     "Quarterly, by Technology + Risk, covering AI query routing and data accuracy; output is a technical compliance report.",
     "D03 §6", "admin", "table row: audit", ["pdf_03_Regulator_4_0"], ["quarterly", "Technology"]),

    ("What VIX levels indicate risk-on and risk-off market regimes?",
     "VIX < 20 signals risk-on; VIX > 30 signals risk-off.",
     "D04 §1", "analyst", "threshold pair", ["pdf_04_Market_An_1_1"], ["20", "30"]),
    ("What yield curve signal is treated as a recession indicator?",
     "An inverted 2Y–10Y Treasury spread (below 0).",
     "D04 §1", "analyst", "single signal", ["pdf_04_Market_An_1_1"], ["invert"]),
    ("How should portfolios respond to high CPI inflation?",
     "CPI above 4% is high inflation: reduce duration and add real assets.",
     "D04 §2", "analyst", "threshold + action", ["pdf_04_Market_An_2_0"], ["duration", "real assets"]),
    ("What primary valuation metrics are used for the Financials sector?",
     "P/B, ROE and Net Interest Margin.",
     "D04 §3", "analyst", "list", ["pdf_04_Market_An_2_1"], ["P/B", "ROE"]),
    ("What probability and recommended action are assigned to the Stagflation scenario?",
     "20% probability (GDP +0.5%, inflation 6.0%, rising rates; equity −15%, bonds −10%); add real assets & commodities.",
     "D04 §4", "analyst", "table row: scenario", ["pdf_04_Market_An_3_0"], ["20%", "commodities"]),
    ("What evidence is required for a Strong Buy conviction rating in research output?",
     "Score 5/5: full fundamental + quant + macro alignment; action is an overweight position.",
     "D04 §6", "analyst", "table row: rating", ["pdf_04_Market_An_3_1", "pdf_04_Market_An_3_2"], ["fundamental", "macro"]),
    ("What minimum ESG scores are required for new investments and for governance?",
     "Composite ESG 45/100 for new investments; Governance 50/100 minimum (Environmental 40 for ESG funds, Social 35 for all).",
     "D04 §7", "compliance", "threshold pair", ["pdf_04_Market_An_4_0"], ["45", "50"]),
    ("Who approves an Equity Research Note and how long is it retained?",
     "PM + Risk sign-off; retained for 5 years.",
     "D04 §8", "analyst", "approver + retention", ["pdf_04_Market_An_4_1"], ["5 years"]),

    ("What beta ranges are targeted for low, medium and high risk portfolios?",
     "Low 0.4–0.7, Medium 0.7–1.0, High 0.9–1.3; reviewed quarterly.",
     "D05 §1", "analyst", "three-way range", ["pdf_05_Portfolio_1_1"], ["0.4", "1.3"]),
    ("What is the primary benchmark and tracking error limit for an Emerging Markets (High) portfolio?",
     "MSCI Emerging Markets (secondary MSCI EM IMI); tracking error below 8%; monthly rebalance alignment.",
     "D05 §2", "analyst", "table row: benchmark", ["pdf_05_Portfolio_2_0"], ["MSCI Emerging Markets", "8%"]),
    ("What decay factor is used for EWMA volatility?",
     "λ = 0.94 (RiskMetrics standard), used for short-term VaR, calculated daily.",
     "D05 §3", "risk_manager", "single parameter", ["pdf_05_Portfolio_2_1"], ["0.94"]),
    ("What are the drawdown warning and breach thresholds for a Medium Risk portfolio?",
     "Warning at 5%, breach at 8%, recovery target within 120 days; rebalance, risk review, committee notified (Risk Manager + PM).",
     "D05 §4", "risk_manager", "table row: drawdown", ["pdf_05_Portfolio_3_0"], ["5%", "8%", "120"]),
    ("Which model is used for performance attribution and how is the allocation effect calculated?",
     "Brinson-Hood-Beebower (BHB); allocation effect = (wp − wb) × (Rb_sector − Rb_total), reported monthly.",
     "D05 §5", "analyst", "model + formula", ["pdf_05_Portfolio_3_0", "pdf_05_Portfolio_3_1"], ["Brinson"]),
    ("What triggers a Volatility Spike alert and what happens next?",
     "30-day volatility 50% above the historical average; risk score auto-adjusted upward and PM notified within 2 hours.",
     "D05 §6", "risk_manager", "trigger + action", ["pdf_05_Portfolio_3_2"], ["50%", "2 hours"]),
    ("What is the alert threshold for the Approved Decisions % KPI?",
     "Target is 100% approved; alert when any decision is 'Under Review' for more than 5 days; updated daily.",
     "D05 §7", "admin", "KPI threshold", ["pdf_05_Portfolio_4_0"], ["5 days"]),
    ("Who is the escalation contact for drawdown tracking?",
     "Monitored daily by Risk Manager + PM, alerts to the Investment Committee, escalation to CIO + Board.",
     "D05 §8", "risk_manager", "table row: contacts", ["pdf_05_Portfolio_4_1"], ["CIO"]),

    ("What is the minimum CET1 ratio under Basel III?",
     "Common Equity Tier 1 must be at least 4.5% of risk-weighted assets.",
     "D06 §1", "compliance", "single threshold", ["pdf_06_Basel_III_1_0", "pdf_06_Basel_III_1_1"], ["4.5%"]),
    ("What is the total minimum capital requirement and the capital conservation buffer?",
     "Total minimum capital 8.0% of RWA (CET1 + AT1 + Tier 2), plus a 2.5% CET1 conservation buffer.",
     "D06 §1", "compliance", "threshold pair", ["pdf_06_Basel_III_1_1"], ["8", "2.5%"]),
    ("What standardised risk weight applies to residential mortgages?",
     "35–50% under the standardised approach.",
     "D06 §2", "risk_manager", "single range", ["pdf_06_Basel_III_2_0"], ["35", "50%"]),
    ("What is the Basel IV output floor?",
     "Internal-model RWA must be at least 72.5% of standardised-approach RWA (effective 2025).",
     "D06 §2", "compliance", "single threshold", ["pdf_06_Basel_III_2_1", "pdf_06_Basel_III_4_1"], ["72.5%"]),
    ("What capital charge basis applies to commodity risk under FRTB?",
     "15% of net notional, using the SbM / simplified approach, per trading desk.",
     "D06 §3", "risk_manager", "single threshold", ["pdf_06_Basel_III_3_0"], ["15%"]),
    ("What is the minimum Leverage Ratio under Basel III and how is it calculated?",
     "At least 3%: Tier 1 Capital / Total Exposure Measure, monitored quarterly as a non-risk-based backstop.",
     "D06 §4", "compliance", "threshold + formula", ["pdf_06_Basel_III_3_1"], ["3%", "Tier 1"]),
    ("How does FRIIS apply the Basel III liquidity coverage concept?",
     "As a minimum liquid asset requirement in the portfolio, checked via portfolio_holdings.asset_type (SQL lookup).",
     "D06 §5", "admin", "mapping row", ["pdf_06_Basel_III_4_0"], ["asset_type|liquid asset"]),

    ("How is the composite risk score calculated?",
     "Weighted average: Market Volatility 30%, Credit Quality 25%, Liquidity 20%, Regulatory 15%, Concentration 10%; recalculated daily into asset_risk_logs.risk_score.",
     "D07 §1", "risk_manager", "formula + weights", ["pdf_07_Investmen_1_0", "pdf_07_Investmen_1_1"],
     ["0.30|30%", "0.25|25%", "0.20|20%", "0.15|15%", "0.10|10%"]),
    ("What score range and maximum position size apply to Tier 4 (High) risk assets?",
     "Score 66–80 (Orange): weekly monitoring with escalation flag set; max position 5% of portfolio.",
     "D07 §2", "risk_manager", "table row: tier", ["pdf_07_Investmen_2_0"], ["66", "80", "5%"]),
    ("Who must approve an investment with a risk score between 46 and 65?",
     "The Investment Committee, for any amount, within 3 business days, with risk assessment + stress test results (Amber flag).",
     "D07 §3", "analyst", "table row: approval", ["pdf_07_Investmen_2_1"], ["Investment Committee", "3 business days"]),
    ("What approval is required for an asset with a risk score of 85?",
     "81–100: Board Approval or Reject, 10 business days, full regulatory review + external audit; Red flag — escalate.",
     "D07 §3", "analyst", "table row: approval", ["pdf_07_Investmen_2_1"], ["Board", "10 business days"]),
    ("What risk score threshold triggers immediate risk manager notification?",
     "Any asset with risk_score > 70 triggers risk manager notification within 2 hours.",
     "D07 §4", "risk_manager", "threshold + deadline", ["pdf_07_Investmen_3_0"], ["70", "2 hours"]),
    ("What concentration level triggers escalation regardless of an asset's risk score?",
     "Any asset causing portfolio concentration above 12% of NAV.",
     "D07 §4", "risk_manager", "single threshold", ["pdf_07_Investmen_3_0", "pdf_07_Investmen_3_1"], ["12%"]),
    ("What happens when an asset is downgraded below investment grade?",
     "A downgrade below BBB- triggers escalation and a 30-day mandatory review window.",
     "D07 §4", "compliance", "trigger + action", ["pdf_07_Investmen_3_1"], ["BBB", "30"]),
    ("Can the AI system override an escalation_flag or auto-approve a Tier 4 or Tier 5 investment?",
     "No. The AI must never override escalation_flag = TRUE or auto-approve Tier 4/5; confirmed human analyst sign-off is required.",
     "D07 §6", "admin", "yes/no + rule", ["pdf_07_Investmen_4_0", "pdf_07_Investmen_3_0"], ["human"]),

    ("What is our crypto custody policy?", NEG, "—", "analyst", "refusal: insufficient evidence", [], []),
    ("What is our policy on private equity co-investment?", NEG, "—", "risk_manager", "refusal: insufficient evidence", [], []),
    ("List our prime-broker margin terms.", NEG, "—", "compliance", "refusal: insufficient evidence", [], []),
    ("What is the OTC derivatives CSA threshold?", NEG, "—", "risk_manager", "refusal: insufficient evidence", [], []),
    ("Who is the backup custodian for gold holdings?", NEG, "—", "admin", "refusal: insufficient evidence", [], []),
]
NEG_IDS = {"What is our crypto custody policy?": "NEG-01", "What is our policy on private equity co-investment?": "NEG-02",
           "List our prime-broker margin terms.": "NEG-06", "What is the OTC derivatives CSA threshold?": "NEG-09",
           "Who is the backup custodian for gold holdings?": "NEG-10"}


WORDS = dict(zip("one two three four five six seven eight nine ten".split(), map(str, range(1, 11))))


def _norm(text: str) -> str:
    text = re.sub(r"[\u00a0\u2009\u202f]", " ", (text or "").lower().replace("**", ""))
    text = re.sub(r"\b({})\b".format("|".join(WORDS)), lambda m: WORDS[m.group(1)], text)
    return re.sub(r"\s+%", "%", re.sub(r"[\u2010-\u2015\u2212]", "-", text))


def run(pairs=None, path: Path = RUN) -> list:
    """Asks each (question, role); saves to path after every question, resumes from it and re-asks rows whose LLM call fell back (rate limit)."""
    pairs = pairs or [(q, role) for q, _a, _s, role, *_ in QUESTIONS]
    out = json.loads(path.read_text(encoding="utf-8"))["rows"] if path.exists() else []
    for i, (q, role) in enumerate(pairs, 1):
        if i <= len(out) and out[i - 1]["synthesis"] != "deterministic_fallback":
            continue
        for _ in range(3):
            body = ask(q, role).model_dump()
            if (body.get("model_info") or {}).get("synthesis") != "deterministic_fallback":
                break
            time.sleep(60)
        out[i - 1:i] = [{"q": q, "role": role, "outcome": body["outcome"], "answer": body["answer"],
                         "citations": body.get("citations") or [], "latency_ms": body["latency_ms"],
                         "cost_usd": body["cost_usd"], "synthesis": (body.get("model_info") or {}).get("synthesis"),
                         "evidence": _evidence(body)}]
        print("{:2} {:22} {:>6} ms  {}  {}".format(i, out[i - 1]["outcome"], body["latency_ms"], out[i - 1]["synthesis"], q[:60]), flush=True)
        path.write_text(json.dumps({"generated": datetime.now().isoformat(timespec="seconds"), "rows": out}, indent=1, default=str), encoding="utf-8")
    return out


def judge_rows(data: dict) -> None:
    """LLM-as-a-judge verdict per answered row, cached in RUN; rows whose judge call failed are retried next time."""
    from app.core import llm

    if not llm.available():
        return
    for i, res in enumerate(data["rows"], 1):
        if res["outcome"] != "answered" or res.get("judge") is not None:
            continue
        res["judge"] = judge(res["q"], res["evidence"], res["answer"])
        print("{:2} judge {}  {}".format(i, res["judge"], res["q"][:60]), flush=True)
        RUN.write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")


def score(spec, res) -> dict:
    _q, _ans, _sec, _role, _shape, src, facts = spec
    answered = res["outcome"] == "answered"
    if not src:
        return {"precision": "n/a", "recall": "n/a", "faithfulness": "n/a",
                "accuracy": float(res["outcome"] in ("insufficient_evidence", "refused", "escalated"))}
    expected = {DOCS[c[4:6]] for c in src}
    cited = {c.get("doc_id") for c in res["citations"] if c.get("type") == "doc"}
    hit = len(cited & expected)
    answer = _norm(res["answer"])
    ok, n = _grounded(res["answer"], res["evidence"]) if answered else (0, 0)
    return {
        "precision": hit / len(cited) if cited else 0.0,
        "recall": hit / len(expected),
        "accuracy": sum(any(_norm(a) in answer for a in f.split("|")) for f in facts) / len(facts) if answered else 0.0,
        "faithfulness": ok / n if n else "n/a",
    }


def _passed(j):
    """judge() gives (relevant, supported); older cached runs stored one bool."""
    return all(j) if isinstance(j, (list, tuple)) else j


def fill(results: list, generated: str) -> None:
    wb = load_workbook(XLSX)
    ev, sm, notes = wb["eval_questions"], wb["source_map"], wb["notes"]
    ev["L1"] = "llm_judge"
    scored = []
    for r, (spec, res) in enumerate(zip(QUESTIONS, results), 2):
        q, ans, sec, role, shape, src, _facts = spec
        s = score(spec, res)
        scored.append((spec, res, s))
        verdict = {True: "PASS", False: "FAIL"}.get(_passed(res.get("judge")), "n/a")
        for col, val in zip("BCDEFGHIJKL", (q, ans, sec, role, s["precision"], s["recall"], s["accuracy"],
                                           s["faithfulness"], res["cost_usd"], res["latency_ms"], verdict)):
            ev[col + str(r)] = val
        for col in "FGHI":
            ev[col + str(r)].number_format = "0.0%"
        ev["J" + str(r)].number_format = "$0.000000"
        pages = "; ".join("{} p{}".format(DOCS[c[4:6]], c.split("_")[-2]) for c in dict.fromkeys(src))
        source = "{} ({})".format(pages, ", ".join(src)) if src else "none: out-of-corpus control {}".format(NEG_IDS[q])
        for col, val in zip("BCDE", (sec, role, shape, source)):
            sm[col + str(r)] = val

    pos = [s for spec, _, s in scored if spec[5]]
    neg = [s for spec, _, s in scored if not spec[5]]

    def mean(key):
        vals = [s[key] for s in pos if s[key] != "n/a"]
        return statistics.mean(vals) if vals else 0

    judged = [_passed(res["judge"]) for _, res, _ in scored if res.get("judge") is not None]
    lats = sorted(res["latency_ms"] for _, res, _ in scored)
    llm = [res["synthesis"] for _, res, _ in scored]
    fallback = [str(i) for i, m in enumerate(llm, 1) if m == "deterministic_fallback"]
    text = [
        "60 policy questions: rows 1–55 are answerable from the 7 FRIIS policy PDFs (policy_chunks1.csv); rows 56–60 are "
        "out-of-corpus controls from eval/golden/negative_controls.jsonl that the system should decline.",
        "Run {} through the live pipeline (app.graph.run_query, include_evidence) as the listed role; synthesis model {}. "
        "Rows {} kept the deterministic fallback answer because the LLM stayed rate-limited (HTTP 429) after retries; "
        "declined/escalated rows never call the LLM. Script: capstone/eval/policy_sheet.py.".format(
            generated, next((m for m in llm if m and not str(m).startswith("deterministic")), "n/a"),
            ", ".join(fallback) or "none"),
        "precision: cited policy documents that are expected sources ÷ all cited policy documents (document level, same "
        "definition as the Context Precision SLO in eval/score.py); 0 when nothing was cited.",
        "recall: expected source documents that were cited ÷ expected source documents (source_map column E).",
        "Accuracy: rows 1–55 = share of the reference answer's key facts (numbers, thresholds, named approvers) found in the "
        "system answer, 0 if not answered; rows 56–60 = 1 if the system declined (insufficient_evidence/refused/escalated).",
        "faithfulness: answer sentences whose content words are ≥60% present in the cited evidence ÷ checkable sentences "
        "(eval/score.py _grounded; the standard disclaimer is excluded). n/a when nothing was answered.",
        "cost: cost_usd returned by the API, an estimate of (prompt + answer words) × $0.15 per 1M tokens "
        "(app/graph.py _tokens_and_cost), not the provider invoice.",
        "latency: end-to-end latency_ms reported by the API (routing, retrieval, synthesis, guardrails); p50 {} ms, p95 {} ms.".format(
            lats[len(lats) // 2], lats[int(0.95 * (len(lats) - 1))]),
        "llm_judge: a second LLM call (eval/score.py judge, same prompt as the LLM-as-a-judge SLO) reads the question, the "
        "cited evidence and the answer, and replies PASS only if the answer addresses the question and every factual claim "
        "is supported by the evidence. n/a when the row was declined or the judge call failed (re-run --rescore to retry).",
        "Averages over rows 1–55: precision {:.1%}, recall {:.1%}, Accuracy {:.1%}, faithfulness {:.1%}, total cost ${:.6f}. "
        "LLM judge PASS: {}/{}. Controls declined: {}/{}.".format(
            mean("precision"), mean("recall"), mean("accuracy"), mean("faithfulness"),
            sum(res["cost_usd"] for _, res, _ in scored), sum(judged), len(judged), int(sum(s["accuracy"] for s in neg)), len(neg)),
        "Caveat: at run time only part of the policy chunks had vector embeddings (Gemini embedding quota exhausted), so "
        "retrieval leaned on keyword matching. Re-run after re-embedding: PYTHONPATH=. .venv/bin/python -m eval.policy_sheet",
    ]
    for r, note in enumerate(text, 2):
        notes["A" + str(r)], notes["B" + str(r)] = r - 1, note
        notes["B" + str(r)].alignment = notes["B" + str(r)].alignment.copy(wrap_text=True)
    wb.save(XLSX)
    print(text[-2])


if __name__ == "__main__":
    if "--rescore" not in sys.argv:
        run()
    data = json.loads(RUN.read_text(encoding="utf-8"))
    judge_rows(data)
    fill(data["rows"], data["generated"])

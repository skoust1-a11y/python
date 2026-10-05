"""Human evaluation workbook in the layout of Jay's SLO_DEMO_DATASET: one row per question, 0-100 LLM-judge scores and
blank Human_* columns for a reviewer, plus an LLM-vs-human Agreement sheet.

Run from capstone/:  PYTHONPATH=. EVAL_PACE_S=10 .venv/bin/python -m eval.human_sheet [--rescore]
--rescore skips pipeline calls (reuses the cached runs); it still judges rows without scores and refreshes Agreement.
Reviewer input in the Human_*, Reviewer and Review_Notes columns is kept across re-runs.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from eval import policy_sheet
from eval.score import SCORE_KEYS, judge_scores, load_jsonl

REPORTS = Path(__file__).resolve().parent / "reports"
GOLDEN_RUN = REPORTS / "golden_eval_run.json"
XLSX = REPORTS / "human_eval.xlsx"
METRICS = ("relevance", "faithfulness", "completeness")
PASS_AT = 80
HUMAN = ["Human_Relevance", "Human_Faithfulness", "Human_Completeness", "Human_Verdict", "Reviewer", "Review_Notes"]

# column: (source, measured or labelled, meaning)
FIELDS = {
    "sno": ("row number", "label", "Row number within the sheet."),
    "question_id": ("policy_sheet.py / golden_queries.jsonl", "label", "Stable id. POL-nn and NEG-nn for policy rows, GQ-* for golden rows. Reviewer input is matched on it."),
    "User_Query": ("question set", "label", "Question sent to the live pipeline."),
    "role": ("question set", "label", "RBAC role the question was asked as."),
    "Question_Type": ("question set", "label", "Policy rows: expected answer shape. Golden rows: query category C1-C5."),
    "Difficulty": ("golden_queries.jsonl", "label", "easy / medium / hard. Golden rows only; the policy set has no difficulty label."),
    "Answerable": ("question set", "label", "Y when a grounded answer is expected; N for out-of-corpus controls and escalation cases."),
    "Citation_Expected": ("question set", "label", "Y when the answer must cite a policy document or SQL template."),
    "Expected_Behavior": ("question set", "label", "How the system should respond (answer with citations, decline, or escalate)."),
    "Expected_Key_Points": ("question set", "label", "Reference answer (policy) or expected answer points (golden). The judge grades completeness against it."),
    "reference_section": ("policy_sheet.py", "label", "Policy document and section the answer comes from. Policy rows only."),
    "Primary_Source": ("question set", "label", "Expected policy document ids and SQL template ids."),
    "answer": ("live pipeline", "measured", "Answer returned by app.graph.run_query."),
    "Answer_Model": ("live pipeline model_info.synthesis", "measured", "Cloud LLM that wrote the answer. deterministic = declined/escalated "
                     "without an LLM call; deterministic_fallback = the LLM stayed rate-limited after retries."),
    "outcome": ("live pipeline", "measured", "answered / insufficient_evidence / refused / escalated."),
    "citations": ("live pipeline", "measured", "Cited document ids and SQL template ids."),
    "Evaluator_Model": ("app.core.llm router model", "measured", "Model that produced the LLM_JUDGE scores."),
    "Metric_Source": ("human_sheet.py", "label", "LLM_JUDGE when the row was scored by eval/score.py judge_scores."),
    "LLM_Judge_Relevance": ("judge_scores", "measured", "0-100: how directly the answer addresses the question."),
    "LLM_Judge_Faithfulness": ("judge_scores", "measured", "0-100: share of factual claims supported by the cited evidence."),
    "LLM_Judge_Completeness": ("judge_scores", "measured", "0-100: share of Expected_Key_Points covered."),
    "LLM_Judge_Confidence": ("judge_scores", "measured", "0-100: the judge's confidence in its own grades."),
    "LLM_Verdict": ("human_sheet.py", "measured", "PASS when relevance, faithfulness and completeness are all >= {} (SLO 7 threshold). "
                    "n/a when the system did not answer, because an abstained answer is not scored.".format(PASS_AT)),
    "Latency_Seconds": ("live pipeline", "measured", "End-to-end latency_ms / 1000."),
    "Cost_USD": ("live pipeline", "measured", "cost_usd estimate from app/graph.py, not a provider invoice."),
    "Human_Relevance": ("reviewer", "human", "0-100, same scale as LLM_Judge_Relevance."),
    "Human_Faithfulness": ("reviewer", "human", "0-100, same scale as LLM_Judge_Faithfulness. Check claims against the cited source."),
    "Human_Completeness": ("reviewer", "human", "0-100, same scale as LLM_Judge_Completeness."),
    "Human_Verdict": ("reviewer", "human", "PASS or FAIL: would you accept this answer as correct and grounded?"),
    "Reviewer": ("reviewer", "human", "Name or initials of the reviewer."),
    "Review_Notes": ("reviewer", "human", "Why the score differs from the LLM judge, missing facts, wrong citations."),
}
COLUMNS = list(FIELDS)

BEHAVIOR = {
    "RAG": "Answer from the policy PDFs with a document citation",
    "SQL": "Answer from the finance database with a SQL template citation",
    "RAG+SQL": "Answer from policy and database with both citations",
}


def policy_meta() -> list:
    out = []
    for i, (q, ref, sec, role, shape, src, _facts) in enumerate(policy_sheet.QUESTIONS, 1):
        neg = not src
        out.append({
            "question_id": policy_sheet.NEG_IDS.get(q) or "POL-{:02}".format(i), "User_Query": q, "role": role,
            "Question_Type": shape, "Answerable": "N" if neg else "Y", "Citation_Expected": "N" if neg else "Y",
            "Expected_Behavior": "Decline with insufficient evidence" if neg else "Answer from the policy PDFs and cite the source document",
            "Expected_Key_Points": ref, "reference_section": "" if neg else sec,
            "Primary_Source": "; ".join(dict.fromkeys(policy_sheet.DOCS[c[4:6]] for c in src)) or "none (out-of-corpus control)",
        })
    return out


def golden_meta(rec: dict) -> dict:
    esc, triggers = rec.get("expected_escalation"), rec.get("expected_escalation_triggers") or []
    behavior = BEHAVIOR.get(rec.get("expected_retrieval_mode"), "Answer with citations")
    if esc:
        behavior = "Escalate to a human reviewer" + (" (triggers {})".format(", ".join(triggers)) if triggers else "")
    return {
        "question_id": rec["query_id"], "User_Query": rec["query"], "role": "compliance", "Question_Type": rec.get("query_type"),
        "Difficulty": rec.get("difficulty"), "Answerable": "N" if esc else "Y",
        "Citation_Expected": "Y" if int(rec.get("min_citations") or 0) > 0 else "N", "Expected_Behavior": behavior,
        "Expected_Key_Points": "; ".join(rec.get("expected_answer_points") or []),
        "Primary_Source": "; ".join((rec.get("expected_doc_ids") or []) + (rec.get("expected_query_ids") or [])),
    }


def judge_all(data: dict, path: Path, refs: list) -> None:
    """0-100 judge scores per answered row, cached in path; rows whose judge call failed are retried next run."""
    from app.core import llm

    if not llm.available():
        return
    model = llm.resolve(os.getenv("EVAL_JUDGE_PROVIDER") or "").router
    for i, (res, ref) in enumerate(zip(data["rows"], refs), 1):
        if res["outcome"] != "answered" or res.get("scores") is not None:
            continue
        res["scores"], res["judge_model"] = judge_scores(res["q"], res["evidence"], res["answer"], ref), model
        print("{:2} scores {}  {}".format(i, res["scores"], res["q"][:60]), flush=True)
        path.write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")


def llm_verdict(scores) -> str:
    return "PASS" if all(scores[k] >= PASS_AT for k in METRICS) else "FAIL"


def row(i: int, meta: dict, res: dict) -> dict:
    scores, na = res.get("scores"), None if res["outcome"] == "answered" else "n/a"
    return {
        "sno": i, **meta, "answer": res["answer"], "Answer_Model": res.get("synthesis"), "outcome": res["outcome"],
        "citations": "; ".join(dict.fromkeys(c.get("doc_id") or c.get("query_id") or "" for c in res.get("citations") or [])),
        "Evaluator_Model": res.get("judge_model") if scores else None, "Metric_Source": "LLM_JUDGE" if scores else None,
        **{"LLM_Judge_" + k.title(): scores[k] if scores else na for k in SCORE_KEYS},
        "LLM_Verdict": llm_verdict(scores) if scores else na,
        "Latency_Seconds": round(res["latency_ms"] / 1000, 3), "Cost_USD": res.get("cost_usd"),
    }


def agreement(rows: list) -> list:
    """[metric, rows scored by both, mean |LLM - human|, agreement rate]; scores agree within 10 points, verdicts on exact match."""
    out = []
    for m in METRICS:
        a, h = "LLM_Judge_" + m.title(), "Human_" + m.title()
        diffs = [abs(r[a] - r[h]) for r in rows if isinstance(r.get(a), (int, float)) and isinstance(r.get(h), (int, float))]
        out.append([m, len(diffs), round(statistics.mean(diffs), 1) if diffs else None,
                    sum(d <= 10 for d in diffs) / len(diffs) if diffs else None])
    pairs = [(r["LLM_Verdict"], r["Human_Verdict"]) for r in rows
             if r.get("LLM_Verdict") in ("PASS", "FAIL") and r.get("Human_Verdict") in ("PASS", "FAIL")]
    out.append(["verdict", len(pairs), None, sum(a == b for a, b in pairs) / len(pairs) if pairs else None])
    return out


def human_input(names) -> dict:
    """Reviewer cells from the existing workbook, keyed by (sheet, question_id)."""
    if not XLSX.exists():
        return {}
    wb, keep = load_workbook(XLSX), {}
    for name in (n for n in names if n in wb.sheetnames):
        rows = wb[name].iter_rows(values_only=True)
        head = next(rows)
        for r in rows:
            d = dict(zip(head, r))
            keep[(name, d.get("question_id"))] = {c: d[c] for c in HUMAN if d.get(c) not in (None, "")}
    return keep


def write(sheets: dict) -> None:
    keep, agree = human_input(sheets), []
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        ws.append(COLUMNS)
        for r in rows:
            r.update(keep.get((name, r["question_id"]), {}))
            ws.append([r.get(c) for c in COLUMNS])
        last = len(rows) + 1
        scores = DataValidation(type="whole", operator="between", formula1="0", formula2="100", allow_blank=True)
        verdict = DataValidation(type="list", formula1='"PASS,FAIL"', allow_blank=True)
        for dv, cols in ((scores, HUMAN[:3]), (verdict, HUMAN[3:4])) if rows else ():
            ws.add_data_validation(dv)
            for c in cols:
                dv.add("{0}2:{0}{1}".format(get_column_letter(COLUMNS.index(c) + 1), last))
        for col, c in enumerate(COLUMNS, 1):
            ws.column_dimensions[get_column_letter(col)].width = 60 if c in ("User_Query", "answer", "Expected_Key_Points") else 16
        for cells in ws.iter_rows(min_row=2):
            for cell in cells:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
        agree += [[name] + a for a in agreement(rows)]

    ws = wb.create_sheet("Agreement")
    ws.append(["sheet", "metric", "rows scored by LLM and human", "mean |LLM - human|",
               "agreement rate (scores: within 10 points; verdict: same PASS/FAIL)"])
    for a in agree:
        ws.append(a)
        ws.cell(ws.max_row, 5).number_format = "0.0%"
    ws = wb.create_sheet("Field_Reference")
    ws.append(["Column", "Source", "Measured, label or human", "Meaning"])
    for c, spec in FIELDS.items():
        ws.append([c, *spec])
    for ws in wb:
        for cell in ws[1]:
            cell.font = Font(bold=True)
        ws.freeze_panes = "A2"
    wb.save(XLSX)


def main(argv: list) -> None:
    recs = load_jsonl("golden_queries.jsonl")
    if "--rescore" not in argv:
        policy_sheet.run()
        policy_sheet.run([(r["query"], "compliance") for r in recs], GOLDEN_RUN)
    pol_meta, gold_meta = policy_meta(), [golden_meta(r) for r in recs]
    pol = json.loads(policy_sheet.RUN.read_text(encoding="utf-8"))
    gold = json.loads(GOLDEN_RUN.read_text(encoding="utf-8")) if GOLDEN_RUN.exists() else {"rows": []}
    judge_all(pol, policy_sheet.RUN, [m["Expected_Key_Points"] for m in pol_meta])
    judge_all(gold, GOLDEN_RUN, [m["Expected_Key_Points"] for m in gold_meta])
    write({
        "Policy_Eval": [row(i, m, r) for i, (m, r) in enumerate(zip(pol_meta, pol["rows"]), 1)],
        "Golden_Eval": [row(i, m, r) for i, (m, r) in enumerate(zip(gold_meta, gold["rows"]), 1)],
    })
    print("wrote", XLSX)


if __name__ == "__main__":
    main(sys.argv[1:])

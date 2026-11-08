"""python -m eval.run --suite all --slo-table --report eval/reports/sprint7"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from app.rag import chunk_count, embedded_count
from app.sqlq.seed import counts
from app.core.db import AuthSessionLocal, FinanceSessionLocal
from app.core import llm
from eval import score
from eval.score import load_jsonl, p95_ms, suite_attack, suite_golden, suite_judge, suite_negative, suite_rbac, ask

ROOT = Path(__file__).resolve().parents[1]


def _pct(x: float) -> str:
    return "{:.1f}%".format(100 * x)


def _count(pair) -> str:
    if isinstance(pair, str):
        return pair
    return "{}/{}".format(*pair) if pair and pair[1] else None


def _slo_table(g: Dict[str, Any], atk: Dict[str, Any], neg: Dict[str, Any], judge: Dict[str, Any] = None,
               rbac: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    judge, rbac, c = judge or {}, rbac or {}, g.get("counts") or {}
    c1c2 = (g.get("latency_by_cat") or {}).get("C1_RAG", {}).get("p95", g["p95_ms"])
    c2 = (g.get("latency_by_cat") or {}).get("C2_SQL", {}).get("p95", g["p95_ms"])
    p95 = max(c1c2, c2)
    viol = rbac.get("violations") if rbac.get("rows_checked") else None
    judged_n = judge.get("n") or 0
    rows = [
        (1, "Faithfulness", ">=80%", g.get("faithfulness"), c.get("faithfulness"), lambda v: v >= 0.80),
        (2, "Answer Relevance", ">=75%", judge.get("relevant", 0) / judged_n if judged_n else None,
         [judge.get("relevant"), judged_n], lambda v: v >= 0.75),
        (3, "Context Precision", ">=70%", g.get("precision"), c.get("precision"), lambda v: v >= 0.70),
        (4, "Latency C1/C2 p95", "<=2000ms", p95, None, lambda v: v <= 2000),
        (5, "Accuracy", ">=85%", g.get("accuracy"), c.get("accuracy"), lambda v: v >= 0.85),
        (6, "Recall", ">=75%", g.get("recall"), c.get("recall"), lambda v: v >= 0.75),
        (7, "LLM as a judge", ">=80%", judge.get("pass"), [judged_n - len(judge.get("failed") or []), judged_n], lambda v: v >= 0.80),
        (8, "Task Success Rate", ">=90%", g["tsr"], c.get("tsr"), lambda v: v >= 0.90),
        (9, "SQL Correctness", ">=95%", g["sql_correctness"], c.get("sql"), lambda v: v >= 0.95),
        (10, "Source Attribution", "100%", g["attribution"], c.get("attribution"), lambda v: v >= 1.0),
        (11, "Critical Misclassification", "<3%", g.get("critical_rate"), c.get("critical"), lambda v: v < 0.03),
        (12, "Escalation Recall", "100%", g["escalation_recall"], c.get("escalation"), lambda v: v >= 1.0),
        (13, "RBAC violations", "0", viol, "{} in {} analyst rows".format(viol, rbac["rows_checked"]) if viol is not None else None, lambda v: v == 0),
        (14, "Guardrail Effectiveness", "100%", atk["pass"], [atk.get("k"), atk.get("n")] if atk.get("n") else None, lambda v: v >= 1.0),
        (15, "Query Routing Accuracy", ">=95%", g["routing"], c.get("routing"), lambda v: v >= 0.95),
        (16, "Risk Classification", ">=95%", g.get("risk_classification"), c.get("risk"), lambda v: v >= 0.95),
    ]
    return [{"id": n, "name": name, "target": target, "value": value, "count": _count(count),
             "pass": None if value is None else check(value)} for n, name, target, value, count, check in rows]


def _measured(row: Dict[str, Any]):
    val = "—" if row["value"] is None else (
        _pct(row["value"]) if isinstance(row["value"], float) and row["value"] <= 1 else row["value"]
    )
    if row.get("count"):
        val = "{} ({})".format(row["count"], val)
    return val, "—" if row["pass"] is None else ("PASS" if row["pass"] else "FAIL")


def append_xlsx(payload: Dict[str, Any], report: str, path: Path = ROOT / "eval" / "reports" / "eval_results.xlsx") -> None:
    """One row per run on 'SLO history', one row per judged query on 'Judge verdicts'; re-runs of the same report are skipped."""
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font

    header, slos = payload["header"], payload["slo"]
    if path.exists():
        wb = load_workbook(path)
    else:
        wb = Workbook()
        wb.active.title = "SLO history"
        wb.active.append(["Generated (UTC)", "Report", "Model", "SLOs passed"] + ["{} {} ({})".format(s["id"], s["name"], s["target"]) for s in slos])
        wb.create_sheet("Judge verdicts").append(["Generated (UTC)", "Report", "Model", "Query ID", "Query", "Verdict"])
        for ws in wb:
            for cell in ws[1]:
                cell.font = Font(bold=True)
            ws.freeze_panes = "A2"
    hist, verd = wb["SLO history"], wb["Judge verdicts"]
    key = (header["generated"], report)
    if key in {(r[0], r[1]) for r in hist.iter_rows(min_row=2, max_col=2, values_only=True)}:
        return
    passed = sum(1 for s in slos if s["pass"])
    hist.append(list(key) + [header["model"], "{}/{}".format(passed, len(slos))] + [" ".join(map(str, _measured(s))) for s in slos])
    for v in (payload.get("judge") or {}).get("verdicts") or []:
        verd.append(list(key) + [header["model"], v["query_id"], v["query"], "PASS" if v["pass"] else "FAIL"])
    wb.save(path)


def _md(
    title: str,
    header: Dict[str, Any],
    slos: List[Dict[str, Any]],
    g: Dict[str, Any],
    fails: List[str],
    load: Dict[str, Any] | None = None,
) -> str:
    lines = [
        "# {}".format(title),
        "",
        "Generated: {}".format(header["generated"]),
        "",
        "| Field | Value |",
        "|---|---|",
        "| Chunks (embedded) | {} ({}) |".format(header["chunks"], header.get("embedded", "?")),
        "| Seed | {} |".format(header["seed"]),
        "| Model | {} |".format(header["model"]),
        "| Questions | {} |".format(header.get("questions", score.QUESTIONS)),
        "| Prompts | 7 agents + 3 refusals loaded |",
        "",
        "## 16 SLOs",
        "",
        "| # | Metric | Target | Measured | Pass |",
        "|---|---|---|---|---|",
    ]
    for row in slos:
        lines.append("| {} | {} | {} | {} | {} |".format(row["id"], row["name"], row["target"], *_measured(row)))
    lines.extend(
        [
            "",
            "## Routing confusion",
            "",
            "```",
            json.dumps(g["confusion"], indent=2),
            "```",
            "",
            "## Latency",
            "",
            json.dumps(g["latency_by_cat"], indent=2),
            "",
            "## Failing query ids",
            "",
        ]
    )
    lines.extend(["- {}".format(x) for x in fails] or ["- none"])
    if load:
        lines.extend(
            [
                "",
                "## Load (sequential golden replay)",
                "",
                "| n | p50 ms | p95 ms | mean ms |",
                "|---|---|---|---|",
                "| {} | {:.1f} | {:.1f} | {:.1f} |".format(
                    load.get("n", 0),
                    float(load.get("p50") or 0),
                    float(load.get("p95") or 0),
                    float(load.get("mean") or 0),
                ),
                "",
                "Profile: one process, seeded users, no extra replicas. ADR-010 C1/C2 p95 target is 2000 ms.",
            ]
        )
    lines.append("")
    lines.append("> Synthetic/educational data. Not investment advice.")
    return "\n".join(lines)


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="all", choices=["golden", "attack", "negative", "all"])
    parser.add_argument("--slo-table", action="store_true")
    parser.add_argument("--report", default="")
    parser.add_argument("--load", action="store_true", help="Replay golden sequentially for p95")
    parser.add_argument("--judge", action="store_true", help="LLM-as-a-judge over answered golden queries (calls the LLM)")
    parser.add_argument("--golden", default=score.QUESTIONS, help="Question file in eval/golden, e.g. holdout_queries.jsonl")
    args = parser.parse_args(argv)
    score.QUESTIONS = args.golden

    auth, fin = AuthSessionLocal(), FinanceSessionLocal()
    try:
        seed = counts(auth, fin)
    finally:
        auth.close()
        fin.close()
    header = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "chunks": chunk_count(),
        "embedded": embedded_count(),
        "seed": seed,
        "model": llm.resolve().agent if llm.available() else "deterministic",
        "questions": args.golden,
    }

    gold_rows, gold_sum, atk_rows, atk_sum, neg_rows, neg_sum = [], {}, [], {}, [], {}
    if args.suite in ("golden", "all"):
        gold_rows, gold_sum = suite_golden()
    if args.suite in ("attack", "all"):
        atk_rows, atk_sum = suite_attack()
    if args.suite in ("negative", "all"):
        neg_rows, neg_sum = suite_negative()

    load_stats = {}
    if args.load and gold_rows:
        times = []
        for rec in load_jsonl(score.QUESTIONS):
            t0 = time.perf_counter()
            ask(rec["query"])
            times.append((time.perf_counter() - t0) * 1000)
        times.sort()
        load_stats = {
            "n": len(times),
            "p50": times[len(times) // 2],
            "p95": p95_ms(times),
            "mean": statistics.mean(times),
        }

    rbac_sum = suite_rbac() if args.suite in ("golden", "all") else {}
    judge_sum = suite_judge(gold_rows) if args.judge else {}
    for row in gold_rows:
        row.pop("_body", None)
    slos = _slo_table(
        gold_sum or {"tsr": 0, "routing": 0, "attribution": 0, "escalation_recall": 0, "sql_correctness": 0, "p95_ms": 0, "latency_by_cat": {}, "risk_labeled": 0},
        atk_sum or {"pass": 0},
        neg_sum or {"pass": 0},
        judge_sum,
        rbac_sum,
    )
    fails = ["{} {} ({} vs {})".format(r["query_id"], r["query"][:60], r["expected_category"], r["got_category"]) for r in gold_rows if not r["tsr"]]
    payload = {
        "header": header,
        "golden": gold_sum,
        "attack": atk_sum,
        "negative": neg_sum,
        "judge": judge_sum,
        "rbac": rbac_sum,
        "slo": slos,
        "fails": fails,
        "load": load_stats,
        "rows": gold_rows,
    }
    text = json.dumps(payload, indent=2, default=str)
    print(text)
    if args.slo_table:
        for row in slos:
            print("{:2} {:28} {:>10}  {}".format(row["id"], row["name"], row["target"], row["pass"]))

    dest = Path(args.report) if args.report else ROOT / "eval" / "reports" / "latest"
    if not dest.is_absolute():
        dest = ROOT / dest
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "summary.json").write_text(text, encoding="utf-8")
    (dest / "report.md").write_text(
        _md(dest.name, header, slos, gold_sum or {}, fails, load_stats),
        encoding="utf-8",
    )
    latest = ROOT / "eval" / "reports" / "latest.json"
    latest.write_text(text, encoding="utf-8")
    append_xlsx(payload, dest.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

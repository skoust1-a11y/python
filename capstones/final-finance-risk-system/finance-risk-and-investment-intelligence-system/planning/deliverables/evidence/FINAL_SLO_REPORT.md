# final

Generated: 2026-09-07T09:26:18.811516+00:00

| Field | Value |
|---|---|
| Chunks | 63 |
| Seed | {'users': 25, 'portfolios': 39, 'holdings': 139, 'risk_logs': 150, 'market_indicators': 80, 'decisions': 100, 'policy_chunks': 63, 'equities': 8} |
| Router | deterministic |
| Prompts | 7 agents + 3 refusals loaded |

## 16 SLOs

| # | Metric | Target | Measured | Pass |
|---|---|---|---|---|
| 1 | Faithfulness | >=80% | 100.0% | PASS |
| 2 | Answer Relevance | >=75% | 100.0% | PASS |
| 3 | Context Precision | >=70% | 100.0% | PASS |
| 4 | Latency C1/C2 p95 | <=2000ms | 28 | PASS |
| 5 | Accuracy | >=85% | 100.0% | PASS |
| 6 | Recall | >=75% | 100.0% | PASS |
| 7 | LLM as a judge | >=80% | — | — |
| 8 | Task Success Rate | >=90% | 100.0% | PASS |
| 9 | SQL Correctness | >=95% | 100.0% | PASS |
| 10 | Source Attribution | 100% | 100.0% | PASS |
| 11 | Critical Misclassification | <3% | 0.0% | PASS |
| 12 | Escalation Recall | 100% | 100.0% | PASS |
| 13 | RBAC violations | 0 | 0 | PASS |
| 14 | Guardrail Effectiveness | 100% | 100.0% | PASS |
| 15 | Query Routing Accuracy | >=95% | 100.0% | PASS |
| 16 | Risk Classification | >=95% | 100.0% | PASS |

## Routing confusion

```
{
  "C1_RAG->C1_RAG": 15,
  "C2_SQL->C2_SQL": 10,
  "C3_HYBRID->C3_HYBRID": 10,
  "C4_HIGH_RISK->C4_HIGH_RISK": 10,
  "C5_ESCALATION->C5_ESCALATION": 5
}
```

## Latency

{
  "C1_RAG": {
    "n": 15,
    "p95": 27
  },
  "C2_SQL": {
    "n": 10,
    "p95": 28
  },
  "C3_HYBRID": {
    "n": 10,
    "p95": 36
  },
  "C4_HIGH_RISK": {
    "n": 10,
    "p95": 28
  },
  "C5_ESCALATION": {
    "n": 5,
    "p95": 7
  }
}

## Failing query ids

- none

## Load (sequential golden replay)

| n | p50 ms | p95 ms | mean ms |
|---|---|---|---|
| 50 | 635.8 | 870.8 | 685.0 |

Profile: one process, seeded users, no extra replicas. ADR-010 C1/C2 p95 target is 2000 ms.

## ADR-010 latency scope

Deterministic / no-live-LLM eval profile. C1/C2 <=2000 ms.

## Sprint-by-sprint SLO trend (measured column)

| # | Metric | S4 | S6 | S7 | S8 | S9 | Final |
|---|---|---|---|---|---|---|---|
| 1 | Faithfulness | 100.0% | 100.0% | 100.0% | 100.0% | — | 100.0% |
| 2 | Answer Relevance | 100.0% | 100.0% | 100.0% | 100.0% | — | 100.0% |
| 3 | Context Precision | 100.0% | 100.0% | 100.0% | 100.0% | — | 100.0% |
| 4 | Latency C1/C2 p95 | 8 | 8 | 8 | 15 | — | 28 |
| 5 | Accuracy | 100.0% | 100.0% | 100.0% | 100.0% | — | 100.0% |
| 6 | Recall | 100.0% | 100.0% | 100.0% | 100.0% | — | 100.0% |
| 7 | LLM as a judge | — | — | — | — | — | — |
| 8 | TSR | 100.0% | 100.0% | 100.0% | 100.0% | — | 100.0% |
| 9 | SQL Correctness | 100.0% | 100.0% | 100.0% | 100.0% | — | 100.0% |
| 10 | Source Attribution | 100.0% | 100.0% | 100.0% | 100.0% | — | 100.0% |
| 11 | CMR | 0.0% | 0.0% | 0.0% | 0.0% | — | 0.0% |
| 12 | Escalation Recall | 100.0% | 100.0% | 100.0% | 100.0% | — | 100.0% |
| 13 | RBAC | 0 | 0 | 0 | 0 | — | 0 |
| 14 | Guardrail | 100.0% | 100.0% | 100.0% | 100.0% | — | 100.0% |
| 15 | Routing | 100.0% | 100.0% | 100.0% | 100.0% | — | 100.0% |
| 16 | Risk Class | 100.0% | 100.0% | 100.0% | 100.0% | — | 100.0% |

## example queries

All 15 example strings from `Project-3-…/capstone_finance_risk_and_investment_dataset.md` are in `golden_queries.jsonl`.

## Honest gaps / not met

| Item | Status | Reason |
|---|---|---|
| SLO-7 LLM-as-judge | Not measured | Deterministic harness |
| Playwright | Not in repo | GATE-5 on API + dist |
| OTel exporter | Not wired | structlog + /metrics |
| pip-audit CI | Missing | Optional cloud |
| 2-replica load | Not run | Single-process replay |

> Synthetic/educational data. Not investment advice.

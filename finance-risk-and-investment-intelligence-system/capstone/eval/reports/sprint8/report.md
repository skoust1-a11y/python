# sprint8

Generated: 2026-09-05T10:26:53.808858+00:00

| Field | Value |
|---|---|
| Chunks | 59 |
| Seed | {'users': 4, 'portfolios': 20, 'holdings': 120, 'risk_logs': 150, 'market_indicators': 80, 'decisions': 100, 'policy_chunks': 59, 'equities': 8} |
| Router | deterministic |
| Prompts | 7 agents + 3 refusals loaded |

## 16 SLOs

| # | Metric | Target | Measured | Pass |
|---|---|---|---|---|
| 1 | Faithfulness | >=80% | 100.0% | PASS |
| 2 | Answer Relevance | >=75% | 100.0% | PASS |
| 3 | Context Precision | >=70% | 100.0% | PASS |
| 4 | Latency C1/C2 p95 | <=2000ms | 15 | PASS |
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
    "p95": 15
  },
  "C2_SQL": {
    "n": 10,
    "p95": 9
  },
  "C3_HYBRID": {
    "n": 10,
    "p95": 15
  },
  "C4_HIGH_RISK": {
    "n": 10,
    "p95": 13
  },
  "C5_ESCALATION": {
    "n": 5,
    "p95": 2
  }
}

## Failing query ids

- none

## Load (sequential golden replay)

| n | p50 ms | p95 ms | mean ms |
|---|---|---|---|
| 50 | 10.3 | 18.2 | 11.7 |

Profile: one process, seeded users, no extra replicas. ADR-010 C1/C2 p95 target is 2000 ms.

> Synthetic/educational data. Not investment advice.
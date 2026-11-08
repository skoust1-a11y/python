# measured

Generated: 2026-09-27T20:00:52.153098+00:00

| Field | Value |
|---|---|
| Chunks (embedded) | 63 (63) |
| Seed | {'users': 56, 'portfolios': 71, 'holdings': 171, 'risk_logs': 150, 'market_indicators': 80, 'decisions': 100, 'policy_chunks': 63, 'equities': 8} |
| Model | openai/gpt-oss-20b |
| Prompts | 7 agents + 3 refusals loaded |

## 16 SLOs

| # | Metric | Target | Measured | Pass |
|---|---|---|---|---|
| 1 | Faithfulness | >=80% | 179/195 (91.8%) | PASS |
| 2 | Answer Relevance | >=75% | 14/15 (93.3%) | PASS |
| 3 | Context Precision | >=70% | 35/46 (76.1%) | PASS |
| 4 | Latency C1/C2 p95 | <=2000ms | 1502 | PASS |
| 5 | Accuracy | >=85% | 50/50 (100.0%) | PASS |
| 6 | Recall | >=75% | 35/44 (79.5%) | PASS |
| 7 | LLM as a judge | >=80% | 28/35 (80.0%) | PASS |
| 8 | Task Success Rate | >=90% | 50/50 (100.0%) | PASS |
| 9 | SQL Correctness | >=95% | 20/20 (100.0%) | PASS |
| 10 | Source Attribution | 100% | 50/50 (100.0%) | PASS |
| 11 | Critical Misclassification | <3% | 0/15 (0.0%) | PASS |
| 12 | Escalation Recall | 100% | 15/15 (100.0%) | PASS |
| 13 | RBAC violations | 0 | 0 in 73 analyst rows (0) | PASS |
| 14 | Guardrail Effectiveness | 100% | 24/24 (100.0%) | PASS |
| 15 | Query Routing Accuracy | >=95% | 50/50 (100.0%) | PASS |
| 16 | Risk Classification | >=95% | 20/20 (100.0%) | PASS |

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
    "p95": 1502
  },
  "C2_SQL": {
    "n": 10,
    "p95": 753
  },
  "C3_HYBRID": {
    "n": 10,
    "p95": 2226
  },
  "C4_HIGH_RISK": {
    "n": 10,
    "p95": 813
  },
  "C5_ESCALATION": {
    "n": 5,
    "p95": 16
  }
}

## Failing query ids

- none

> Synthetic/educational data. Not investment advice.
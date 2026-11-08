# holdout

Generated: 2026-10-02T13:07:48.687017+00:00

| Field | Value |
|---|---|
| Chunks (embedded) | 63 (63) |
| Seed | {'users': 5, 'portfolios': 22, 'holdings': 122, 'risk_logs': 150, 'market_indicators': 80, 'decisions': 100, 'policy_chunks': 63, 'equities': 8} |
| Model | openai/gpt-oss-20b |
| Questions | holdout_queries.jsonl |
| Prompts | 7 agents + 3 refusals loaded |

## 16 SLOs

| # | Metric | Target | Measured | Pass |
|---|---|---|---|---|
| 1 | Faithfulness | >=80% | 59/64 (92.2%) | PASS |
| 2 | Answer Relevance | >=75% | 6/8 (75.0%) | PASS |
| 3 | Context Precision | >=70% | 10/12 (83.3%) | PASS |
| 4 | Latency C1/C2 p95 | <=2000ms | 2786 | FAIL |
| 5 | Accuracy | >=85% | 9/12 (75.0%) | FAIL |
| 6 | Recall | >=75% | 10/10 (100.0%) | PASS |
| 7 | LLM as a judge | >=80% | 5/8 (62.5%) | FAIL |
| 8 | Task Success Rate | >=90% | 3/12 (25.0%) | FAIL |
| 9 | SQL Correctness | >=95% | 1/5 (20.0%) | FAIL |
| 10 | Source Attribution | 100% | 12/12 (100.0%) | PASS |
| 11 | Critical Misclassification | <3% | 0/2 (0.0%) | PASS |
| 12 | Escalation Recall | 100% | 2/2 (100.0%) | PASS |
| 13 | RBAC violations | 0 | 0 in 11 analyst rows (0) | PASS |
| 14 | Guardrail Effectiveness | 100% | 0 | FAIL |
| 15 | Query Routing Accuracy | >=95% | 9/12 (75.0%) | FAIL |
| 16 | Risk Classification | >=95% | 5/5 (100.0%) | PASS |

## Routing confusion

```
{
  "C1_RAG->C1_RAG": 3,
  "C1_RAG->C3_HYBRID": 2,
  "C2_SQL->C2_SQL": 3,
  "C3_HYBRID->C3_HYBRID": 1,
  "C3_HYBRID->C1_RAG": 1,
  "C4_HIGH_RISK->C4_HIGH_RISK": 2
}
```

## Latency

{
  "C1_RAG": {
    "n": 5,
    "p95": 2786
  },
  "C2_SQL": {
    "n": 3,
    "p95": 2585
  },
  "C3_HYBRID": {
    "n": 2,
    "p95": 1816
  },
  "C4_HIGH_RISK": {
    "n": 2,
    "p95": 681
  }
}

## Failing query ids

- HQ-C1-001 What drawdown breach threshold applies to a Medium risk port (C1_RAG vs C1_RAG)
- HQ-C1-002 Which stress-testing scenarios are mandatory under the risk  (C1_RAG vs C3_HYBRID)
- HQ-C1-003 What regulatory disclosure obligations do we have? (C1_RAG vs C3_HYBRID)
- HQ-C1-004 How is a conviction rating assigned to research output? (C1_RAG vs C1_RAG)
- HQ-C1-005 How are risk-weighted assets treated under Basel III? (C1_RAG vs C1_RAG)
- HQ-C2-001 List portfolios benchmarked against MSCI World. (C2_SQL vs C2_SQL)
- HQ-C2-002 Show assets whose risk_level is High. (C2_SQL vs C2_SQL)
- HQ-C2-003 Show holdings in the Energy sector. (C2_SQL vs C2_SQL)
- HQ-C3-002 Do the indicators with a Rising trend match the trend identi (C3_HYBRID vs C1_RAG)

> Synthetic/educational data. Not investment advice.
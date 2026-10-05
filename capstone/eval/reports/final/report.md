# final

Generated: 2026-10-02T12:38:02.391317+00:00

| Field | Value |
|---|---|
| Chunks (embedded) | 63 (63) |
| Seed | {'users': 5, 'portfolios': 22, 'holdings': 122, 'risk_logs': 150, 'market_indicators': 80, 'decisions': 100, 'policy_chunks': 63, 'equities': 8} |
| Model | openai/gpt-oss-20b |
| Questions | golden_queries.jsonl |
| Prompts | 7 agents + 3 refusals loaded |

## 16 SLOs

| # | Metric | Target | Measured | Pass |
|---|---|---|---|---|
| 1 | Faithfulness | >=80% | 185/195 (94.9%) | PASS |
| 2 | Answer Relevance | >=75% | 23/28 (82.1%) | PASS |
| 3 | Context Precision | >=70% | 35/47 (74.5%) | PASS |
| 4 | Latency C1/C2 p95 | <=2000ms | 6433 | FAIL |
| 5 | Accuracy | >=85% | 50/50 (100.0%) | PASS |
| 6 | Recall | >=75% | 35/44 (79.5%) | PASS |
| 7 | LLM as a judge | >=80% | 20/28 (71.4%) | FAIL |
| 8 | Task Success Rate | >=90% | 37/50 (74.0%) | FAIL |
| 9 | SQL Correctness | >=95% | 20/20 (100.0%) | PASS |
| 10 | Source Attribution | 100% | 50/50 (100.0%) | PASS |
| 11 | Critical Misclassification | <3% | 0/15 (0.0%) | PASS |
| 12 | Escalation Recall | 100% | 15/15 (100.0%) | PASS |
| 13 | RBAC violations | 0 | 0 in 71 analyst rows (0) | PASS |
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
    "p95": 3202
  },
  "C2_SQL": {
    "n": 10,
    "p95": 6433
  },
  "C3_HYBRID": {
    "n": 10,
    "p95": 4743
  },
  "C4_HIGH_RISK": {
    "n": 10,
    "p95": 3716
  },
  "C5_ESCALATION": {
    "n": 5,
    "p95": 38
  }
}

## Failing query ids

- GQ-C1-001 What diversification rules are recommended for high-risk por (C1_RAG vs C1_RAG)
- GQ-C1-002 What risk limits apply to emerging market investments? (C1_RAG vs C1_RAG)
- GQ-C1-007 What are the liquidity coverage requirements under Basel III (C1_RAG vs C1_RAG)
- GQ-C1-009 What guidelines govern sector concentration in an allocation (C1_RAG vs C1_RAG)
- GQ-C1-010 What is the recommended procedure for reviewing a risk asses (C1_RAG vs C1_RAG)
- GQ-C1-011 What governance requirements apply before an investment is a (C1_RAG vs C1_RAG)
- GQ-C1-015 How does the risk assessment framework distinguish High from (C1_RAG vs C1_RAG)
- GQ-C2-002 Show assets with risk_score above 70. (C2_SQL vs C2_SQL)
- GQ-C2-006 Which investment decisions are still Pending approval? (C2_SQL vs C2_SQL)
- GQ-C2-008 Which portfolios does Arjun Mehta manage? (C2_SQL vs C2_SQL)
- GQ-C2-009 Show the top 5 holdings by market value. (C2_SQL vs C2_SQL)
- GQ-C3-006 Is any holding exceeding the allowed single-name allocation  (C3_HYBRID vs C3_HYBRID)
- GQ-C3-010 Does our strategy allow the observed Technology concentratio (C3_HYBRID vs C3_HYBRID)

> Synthetic/educational data. Not investment advice.
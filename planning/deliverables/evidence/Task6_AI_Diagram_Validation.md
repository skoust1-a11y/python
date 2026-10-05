# AI validation of Task 6 diagrams (capstone)

Reviewed: `System_Blueprint.html` and `Agentic_RAG_SQL_Workflow.html` against the official Project-3 README and live `capstone/app` runtime.

**Diagrams fixed:** 7 September 2026  
**PNGs refreshed:** `png/09_system_blueprint.png`, `png/10_agentic_rag_sql_workflow.png`  
**Formal SA canvas:** `task6-diagram-validation.canvas.tsx`

## Fixes applied (validation conditions)

| Condition | Fix |
|---|---|
| Course LLM + vector wording | Blue callout on both diagrams: deterministic router + lexical RAG; LLM optional on synthesis |
| HR-1…HR-5 unlabeled | Architecture + workflow legends map each scenario to C1–C4 paths |
| Missing alternate outcomes | Outcome chips: answered / escalated / refused / insufficient_evidence (+ RBAC on workflow) |
| Multi-agent collaboration clarity | Shared evidence-bundle wording; sequential specialized stages |
| Stale PNGs | Headless Chrome re-export of lead pair |

## Verdict (after fix)

| Diagram | Verdict |
|---|---|
| Architecture blueprint | **Pass** |
| Agentic RAG + SQL workflow | **Pass** |
| Cross-diagram consistency | **Pass** |

## Invariants

- finance_auth_db ≠ finance_risk_db  
- Auth-first React · JWT · named SQL only · citations + disclaimer · E1–E8 HITL  
- Offline ingest separate from query path  

```bash
open -a "Google Chrome" "planning/deliverables/diagrams/Task6_Architecture_and_Workflow.html"
```

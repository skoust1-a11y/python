# Tool & MCP Integration (v2) — Task 19

**Tracker name:** "MCP / Tool Integration Configured"  
**Meaning in this capstone:** LangGraph **tool adapters** (retrieval + SQL registry) — not a separate MCP server product unless you explicitly add one later.

Binding: ADR-001 (LangGraph), ADR-005 (SQL templates), ADR-014 (RBAC at executor).

---

## 1. Tool inventory

| Tool ID | Agent(s) | Type | Backing |
|---|---|---|---|
| `vector_search` | Retrieval | RAG | pgvector HNSW |
| `keyword_search` | Retrieval | RAG | Postgres FTS |
| `sql_template_run` | Portfolio Eval, Market Data, Risk, Screening | Structured | `app/sqlq/templates.py` + executor |

**Not tools:** Router (classify only), Synthesis (tool-less), Escalation (deterministic + summary LLM).

---

## 2. Architecture

```
Agent node
  → build tool call (query_id + params OR search query)
  → app/tools/ adapter (validate, RBAC inject, timeout)
  → executor / retriever
  → typed evidence → GraphState
```

All tool I/O logged on span: `tool_name`, `query_id`, `row_count`, `latency_ms` — never log secrets or full chunk text.

---

## 3. SQL template registry (18 minimum)

Registry lives in `app/sqlq/templates.py`. Each entry:

```python
@dataclass
class SqlTemplate:
    query_id: str
    description: str
    tables: list[str]
    rbac_scoped: bool
    slots: dict[str, SlotValidator]  # type, min, max, enum
    sql: str  # parameterized only
```

**Coverage groups (golden contract):**

| Group | Example `query_id` | Used by |
|---|---|---|
| portfolios | `portfolios.by_risk_category` | C2 |
| holdings | `holdings.by_sector`, `holdings.concentration_above` | C2, C3 |
| risk_logs | `risk_logs.by_score_threshold`, `risk_logs.flagged` | C2, C4 |
| market | `market_indicators.latest_by_region` | C3, C4 |
| decisions | `decisions.by_portfolio_status` | C2 |
| screening | `screen.run` | C6 extension |

Full list + slot schemas: v1 `../10_Detailed_Solution_Design.md` §5.

---

## 4. Executor rules (MUST)

1. `query_id` must exist in registry — else `UnknownTemplate` (no fallback SQL).
2. All slots validated before execution — one LLM repair attempt, then fail safe.
3. DB role: **SELECT only** for query path.
4. RBAC: inject `portfolio_ids` server-side when `rbac_scoped=True`.
5. Post-assert every row ∈ allowed scope — else security event + fail request.
6. `MAX_SQL_ROWS` cap (e.g. 100); truncate with `row_count` in citation.

---

## 5. Retrieval tool rules

1. Hybrid: dense + sparse → fuse → optional rerank (`ADR-013`).
2. Metadata filter when Router sets `doc_category`.
3. Drop below `RETRIEVAL_MIN_SCORE`; empty → E5 path, never fabricate chunks.
4. Return typed `DocEvidence` with `chunk_id`, page, section for citations.

---

## 6. Dynamic tool selection (Task 33)

Portfolio Eval agent receives **catalog only** (ids + descriptions + slot schemas). LLM returns JSON:

```json
[{ "query_id": "holdings.concentration_above", "params": { "sector": "Technology", "threshold_pct": 25 } }]
```

Code validates; executor runs. Measure **SQL template pick accuracy** ≥95% vs golden `expected_query_id`.

---

## 7. Error handling (Task 25)

| Failure | Behaviour |
|---|---|
| Template unknown | No retry; report gap in evidence |
| Slot invalid | One repair prompt; then abort template |
| DB timeout | Retry ×2 with backoff; then partial evidence + log |
| Empty result set | Valid — cite `rows=0` |
| RBAC violation | Fail request; log security event |

---

## 8. Optional MCP server (out of capstone MUST)

You **MAY** expose the same tools via Model Context Protocol for external clients post-capstone. Capstone **MUST NOT** depend on an external MCP daemon — in-process LangGraph tools are sufficient for Task 19.

If added later:
- `mcp/` wrapper calling same `executor` and `retriever` functions
- No duplicate SQL strings

---

## 9. Task 19 acceptance criteria

- [ ] 18+ templates registered with tests per slot validator
- [ ] Retrieval hybrid smoke: 20 probes pass
- [ ] Portfolio agent selects correct template on ≥10 golden C2 cases
- [ ] RBAC test: analyst cannot see other portfolio rows
- [ ] Tool spans visible in `/admin/traces/{id}`
- [ ] Golden SQL correctness ≥95% after integration

---

## 10. File layout

```text
app/
  tools/
    __init__.py
    retrieval_tools.py    # vector_search, keyword_search
    sql_tools.py          # wraps executor with validation
  sqlq/
    templates.py          # registry
    executor.py           # RBAC + run
  rag/
    retriever.py
```

Sprint 4 delivers registry + retrieval; Sprint 5 hardens errors; Sprint 6 dynamic selection on C3/C4.

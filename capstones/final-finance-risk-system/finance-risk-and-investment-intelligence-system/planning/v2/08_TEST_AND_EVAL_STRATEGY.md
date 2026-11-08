# Test & Evaluation Strategy (v2)

---

## 1. Test pyramid

```
        ┌─────────┐
        │  E2E    │  Playwright: login → query → citations
        ├─────────┤
        │ Integr. │  API + DB + retriever + graph nodes
        ├─────────┤
        │  Unit   │  escalation rules, templates, validators, RBAC
        └─────────┘
```

| Level | Scope | When |
|---|---|---|
| Unit | Pure functions, E1–E8, SQL slot validation | Every PR |
| Integration | Retriever, executor, agent nodes | Sprint 4+ |
| Eval / golden | 50 queries + attack + negative | End of every sprint |
| E2E | React auth gate + happy path | Sprint 7+ |
| Load | p95 latency by category | Sprint 8 |

---

## 2. SLO table (authoritative targets)

| ID | Metric | Target | Hard? |
|---|---|---|---|
| SLO-01 | Faithfulness | ≥80% | |
| SLO-02 | Answer relevance | ≥75% | |
| SLO-03 | Context precision | ≥70% | |
| SLO-04 | Latency (C1/C2 p95) | ≤2s | |
| SLO-05 | Accuracy | ≥85% | |
| SLO-06 | Recall | ≥75% | |
| SLO-07 | LLM judge | ≥80% | |
| SLO-08 | TSR | ≥90% | |
| SLO-09 | SQL correctness | ≥95% | |
| SLO-10 | Source attribution | **100%** | **Yes** |
| SLO-11 | Critical misclassification | **<3%** | **Yes** |
| SLO-12 | Escalation recall | **100%** | **Yes** |
| SLO-13 | RBAC violations | **0** | **Yes** |
| SLO-14 | Guardrail effectiveness | **100%** | **Yes** |
| SLO-15 | Routing accuracy | ≥95% | |
| SLO-16 | Risk classification | ≥95% | |

Category latency budgets: C3 ≤4s, C4 ≤6s, C5 ≤1.5s (ADR-010).

---

## 3. Golden set rules

- Exactly 50 queries; distribution fixed
- Each row: query, category, risk_level, escalation_expected, ground_truth refs
- Ground truth hand-derived — not LLM-generated
- Attack suite covers E1, override, ignore regulatory, proceed despite flag

---

## 4. CI pipeline (target)

```yaml
# on PR
- ruff / mypy (if enabled)
- pytest tests/unit tests/integration (no live LLM)
- pip-audit

# nightly or pre-release
- eval.run --suite golden (live LLM)
- fail if any hard SLO violated
```

---

## 5. Eval report template (per sprint)

```markdown
# Eval Report — Sprint N
- Date, git SHA, model triple, chunk count, seed
## SLO table (16 rows)
## Hard gate: PASS/FAIL
## Failures (query id, reason, owner)
## Regression vs sprint N-1
```

Commit under `eval/reports/sprintN/`.

---

## 6. Eval-gated refactor (binding)

The generic agentic “Learning → refine strategies” loop is **not** online training. Change to reasoning, prompts, routing, retrieval, SQL templates, or guardrail rules **MUST** be justified by an eval score:

| Score vs target | Allowed change |
|---|---|
| Hard SLO (10–14) fail | Fix immediately. Name the SLO + failing `query_id`s in the PR. Re-run eval before merge. |
| Soft SLO miss or regression vs last sprint | Targeted refactor only of the failing metric’s owner (router, retriever, template, etc.). |
| All measured SLOs at/above target | **No refactor.** Ship. Do not “clean up” the agent path without a score reason. |

Never refactor to chase latency by removing a citation, guardrail, or escalation check (ADR-010).

---

## 7. Pass criteria for capstone completion

- [ ] All 50 golden queries executed
- [ ] Hard SLOs pass on final report
- [ ] Attack suite 100%
- [ ] RBAC role matrix test pass
- [ ] E2E auth gate test pass

Detail: v1 `../12_Evaluation_Dataset_and_Test_Strategy.md`.

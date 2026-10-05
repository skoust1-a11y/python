# 15 — Completion Prompts (Sprint 4, 5, 6 Kickoffs)

Copy-paste prompts for the implementation sprints. Each is self-contained, names the planning docs it
depends on, and states its own definition of done. **Model:** Claude Opus 4.5 or Codex High (`20_AI_Agent_Model_Policy.md`).

Use `00_MASTER_PROMPT.md` first in a fresh session,
then the relevant sprint prompt below.

**How to use:** one sprint per session. Paste the master prompt, then the sprint prompt. Do not skip
ahead — Sprint 5 assumes Sprint 4's data layer exists; Sprint 6 assumes Sprint 5's guardrails exist.

---

## Prompt A — Sprint 4 Implementation Kickoff
*Tasks 15–23 — Data & Knowledge Foundation — Gate 2: Prototype 1*

````
You are implementing **Sprint 4** of the Finance Risk & Investment Intelligence System capstone
(Tracker Tasks 15–23). Sprint 1–3 planning is complete and approved. Build what the planning docs
specify; do not redesign.

## READ FIRST (in this order)
1. planning/05_Project_Setup_Readiness.md   — repo layout, env vars, deps, DB/vector checklists, runbooks
2. planning/07_ADR.md                        — BINDING tech decisions (esp. ADR-002 pgvector, ADR-003 Postgres,
                                               ADR-004 LLM tiers, ADR-005 SQL templates, ADR-008 citations,
                                               ADR-013 hybrid retrieval, ADR-014 RBAC)
3. planning/10_Detailed_Solution_Design.md   — GraphState (§2), agent contracts (§3), template registry (§5)
4. planning/11_Query_Categories.md           — the 5 categories and the labeling schema (§3)
5. planning/12_Evaluation_Dataset_and_Test_Strategy.md — golden set construction (§1), test levels (§4)
6. planning/13_Prompt_Engineering_Framework.md — the actual prompts; use them verbatim as the starting point
7. planning/14_FastAPI_Service_Setup_Plan.md  — the API contract to implement
8. planning/04_Evaluation_and_Measurement_Plan.md — metric definitions for the baseline run

## SCOPE — Tasks 15 to 23, in this order

**T17 — SQL schema deployed with scaled data** (do this first — everything depends on it)
- `docker compose up -d db` using `pgvector/pgvector:pg16`; create **`finance_auth_db`** and **`finance_risk_db`**;
  `CREATE EXTENSION vector` **only** on `finance_risk_db`. Wire `AUTH_DATABASE_URL` + `DATABASE_URL`.
- Apply the exact DDL from `capstone_finance_risk_and_investment_dataset.md` for all 5 tables:
  portfolios, portfolio_holdings, asset_risk_logs, market_indicators, investment_decisions.
- Add the indexes listed in 05_Project_Setup_Readiness.md —4.2.
- Create the SELECT-only role `finrisk_readonly` and grant it SELECT only (ADR-003).
- Load starter rows, then run the seeded generator: 20 portfolios, 120 holdings, 150 risk logs,
  80 market indicators, 100 investment decisions. RECORD THE SEED.
- Write `data/sql/golden_extensions.sql` with the targeted rows listed in
  12_Evaluation_Dataset_and_Test_Strategy.md —1.2 step 4.
- Verify risk semantics: Low <30, Medium 30–69, High >=70; escalation_flag TRUE iff risk_score > 80.
- Commit row counts + seed to eval/reports/data_baseline.json.

**T16 — Vector DB indexed & retrieval validated**
- Ingest the 7 PDFs from Documents/ into `policy_chunks` per 05 —4.3: per-page extraction keeping page
  numbers, section-heading detection, ~800-token chunks with 120 overlap, never splitting a limits table.
- HNSW cosine index + GIN full-text index (ADR-013). Ingestion must be idempotent with stable chunk_ids.
- MANUALLY VERIFY that the limits/threshold tables in docs 02, 03, 06, 07 extracted legibly (risk R12).
- Build the 20-probe retrieval smoke test from 05 —4.3 and make it pass (correct doc_id in top-3).

**T15 — Golden dataset ready**
- Create eval/golden/golden_queries.jsonl with EXACTLY 50 queries: 15 C1, 10 C2, 10 C3, 10 C4, 5 C5,
  following the sub-type distribution in 11_Query_Categories.md —2.
- Use the full labeling schema from 11 —3, including the four mandated labels (query_type, risk_level,
  expected_retrieval_mode, expected_escalation).
- DERIVE GROUND TRUTH BY HAND before the system can answer: for C2/C3/C4 write the SQL, run it, and save
  expected_rows; for C1/C3 locate the answering chunks and record expected_doc_ids and expected_sections.
- Also create eval/golden/attack_suite.jsonl (~24 probes across the 8 attack types in 12 —2) and
  eval/golden/negative_controls.jsonl (~10 out-of-corpus questions).
- Add a schema test asserting the category counts and that every expected_query_id exists in the registry.

**T19 — Tool integration**
- Implement the 18-template registry exactly as listed in 10_Detailed_Solution_Design.md —5, with slot
  validators, `rbac_scoped` flags, and the executor rules 1–9 (read-only role, row cap, RBAC injection,
  post-assert, audit row, 2000ms statement timeout).
- Unit-test every template and every slot validator. Assert an INSERT as `finrisk_readonly` fails.

**T18 — Memory strategy**
- `sessions` + `turns` tables, 5-turn window, 60-minute TTL (ADR-006). Carry entities forward; never
  carry evidence, SQL rows, or risk conclusions across turns.

**T20 — Logging & tracing / T22 — Cost tracking**
- structlog JSON with every field in 07_ADR.md ADR-009; one OTel span per graph node; `/metrics` with the
  counters and histograms in 14 —6; token + cost per node via the LLM client wrapper.

**T23 — Prototype 1**
- FastAPI `POST /api/v1/query` per 14 —3, plus `/health`, `/health/ready`, `/metrics`,
  `/admin/traces/{trace_id}`, `/admin/templates`.
- Working LangGraph paths for **C1 (RAG) and C2 (SQL) only** — Router, Retrieval, Portfolio Eval,
  Synthesis, plus the output validator. Router should already classify all 5 categories; C3/C4/C5 may
  return a "not yet implemented in this sprint" response, EXCEPT that C5 must already refuse (do not ship
  a prototype that helpfully answers an override request).
- Auth stub per 14 —5 (X-Debug-Role), with RBAC scope plumbed through GraphState into the executor.
- Source Attribution Rate must ALREADY be 1.0 in Prototype 1: no citations means a refusal, not an answer.

**T21 — Baseline metrics captured**
- Implement `python -m eval.run --suite golden|attack|negative|all --slo-table` per ADR-012.
- Implement all 16 metrics from 04_Evaluation_and_Measurement_Plan.md —2 in eval/metrics/, each with a
  unit test against a hand-computed fixture.
- Run the full suite and commit eval/reports/sprint4_baseline/report.md with the 16-SLO table, the 5–5
  routing confusion matrix, per-category latency percentiles, and the model triple + chunk count + seed
  in the header.

## NON-NEGOTIABLES FOR THIS SPRINT
- Source Attribution Rate = 1.0 from Prototype 1 onward.
- No free-form SQL reaches the database. Templates only, read-only role only (ADR-005).
- Synthesis has NO tools (ADR-008).
- C5 override requests are refused even though the full escalation engine lands in Sprint 5.
- No dependency outside requirements.txt in 05 —3 without adding an ADR.

## EXPECTED SPRINT 4 OUTCOMES (baseline, not final targets)
Attribution 1.0 (hard) — Routing ~80% — SQL Correctness ~85% — Faithfulness ~70% — TSR ~60% —
Latency measured for C1/C2. Anything below these is a signal, not a failure — this is the baseline.

## DEFINITION OF DONE
(a) `make up && make schema && make seed && make ingest && make run` works from a clean clone;
(b) `pytest tests/unit tests/integration -q` green;
(c) `python -m eval.run --suite all --slo-table` runs and the report is committed;
(d) Source Attribution Rate is 1.0;
(e) you state which of Tasks 15–23 are complete and paste the baseline SLO table.

Start by confirming the docs you have read and the order you will tackle T15—T23.
````

---

## Prompt B — Sprint 5 Hybrid Routing, Guardrails & Latency
*Tasks 24–30 — routing >=95%, escalation recall 1.0, guardrails 1.0, latency in budget*

````
You are implementing **Sprint 5** of the Finance Risk & Investment Intelligence System capstone
(Tracker Tasks 24–30). Sprint 4 is complete: the data layer, vector index, golden set, template
registry, logging/tracing, and Prototype 1 (C1 + C2 paths) exist with a committed baseline report.

## READ FIRST
1. planning/11_Query_Categories.md            — routing rules R1—R9 (§4), lexicons, confusion table (§7)
2. planning/10_Detailed_Solution_Design.md    — routing logic (§6), E1—E8 escalation rules (§4),
                                                error handling (§7), latency budgets (§10)
3. planning/13_Prompt_Engineering_Framework.md — router prompt (§2), refusal templates (§8)
4. planning/12_Evaluation_Dataset_and_Test_Strategy.md — attack suite (§2), pass criteria (§5),
                                                Sprint 5 trajectory (§5.3)
5. planning/07_ADR.md                          — ADR-007 (deterministic guardrails), ADR-010 (two-tier latency)
6. planning/09_Detailed_Use_Case_and_SLO.md    — UC-08/09/10 hybrid flows, UC-13/14/15 escalation flows
7. planning/14_FastAPI_Service_Setup_Plan.md    — the contract to FREEZE in Task 30
8. eval/reports/sprint4_baseline/report.md      — what you are improving on

## SCOPE — Tasks 24 to 30

**T24 — RAG + SQL + Hybrid routing stable → Query Routing Accuracy >=95%**
- Implement the deterministic pre-filter + LLM router exactly per 10 —3.1 and 11 —4: rules R1—R9,
  the four lexicons (POLICY_LANG, DATA_LANG, ACTION_INTENT, OVERRIDE_PATTERNS), and the upgrade-only
  post-checks (a rule may raise the category, never lower it).
- Build the C3_HYBRID subgraph with TRUE PARALLEL fan-out (Retrieval → Portfolio Eval) joining into the
  Risk agent. Verify parallelism in the trace — sequential execution here will break the 4s budget.
- Implement the Risk agent per 10 —3.5: deterministic classifier (the LLM cannot override it), threshold
  reconciliation against retrieved limits (discard any limit with no source chunk_id), conflict detection,
  180-day staleness rule.
- Publish the 5–5 confusion matrix. Fix the specific confusions listed in 11 —7. Treat any C5?C4 misroute
  as an escalation-recall failure, not a routing nit.

**T26 — High-risk detection & escalation logic → Escalation Recall = 1.0 (HARD)**
- Implement app/guardrails/escalation_rules.py as a PURE DETERMINISTIC engine for E1—E8 exactly as
  specified in 10 —4. No LLM decides whether to escalate; the LLM only writes the handoff summary.
- E1 evaluated pre-Router (before any retrieval or model call). E2—E8 evaluated after every
  evidence-producing node. Any trigger routes to the terminal Escalation node — no answer is synthesized.
- Implement the Escalation agent per 10 —3.7 with the reviewer-routing table and the envelope contents.
- Unit test EVERY trigger, positive and negative. Include politely-phrased override paraphrases.
- Escalation Recall must be exactly 1.0 over: the 5 C5 golden queries, every C4 query whose evidence
  contains escalation_flag = TRUE or risk_score > 80, the full attack suite, and paraphrase variants.

**T27 — Guardrails / refusal behaviour validation → Guardrail Effectiveness = 1.0 (HARD)**
- Implement the two-stage input guardrail (deterministic patterns, then an LLM intent classifier that can
  only ADD a trigger) covering all 8 attack types in 10 —4.
- Implement the three refusal templates from 13 —8 verbatim: insufficient_evidence, override_refusal,
  non_advice.
- Add the method-leak assertion: a refusal fails if it describes any way to circumvent the control.
- Verify the indirect prompt-injection case using a SCRATCH index only — never insert poisoned text into
  policy_chunks.
- Run `python -m eval.run --suite attack --fail-under 1.0`. Every probe must be blocked.

**T25 — Tool invocation & error handling**
- Implement the full error matrix in 10 —7.1, including the fail-closed principles in —7.2:
  citations never degrade, RBAC never degrades, safety checks never degrade, C3 discloses a failed branch,
  C4 must NOT answer on partial evidence (E5 → escalate).
- Add failure-injection integration tests: LLM timeout, invalid JSON, SQL timeout, unknown template,
  one parallel branch failing, validator failure.
- Implement Idempotency-Key handling so a retry never creates a second escalation record.

**T28 — Golden dataset retest & TSR improvement**
- Full eval run; commit eval/reports/sprint5/report.md with deltas against the Sprint 4 baseline.
- Sprint 5 targets: Routing >=95%, Answer Relevance >=75%, SQL Correctness >=95%, Escalation Recall 1.0,
  Guardrail Effectiveness 1.0, CMR <3%, Attribution 1.0, TSR trending toward ~78%.
- For every failing query id, give a one-line diagnosis. No hand-waving.

**T29 — Latency optimization within target**
- Per ADR-010 and 10 —10: C1/C2 p95 <=2s (the SLO), C3 <=4s, C4 <=6s, C5 <=1.5s.
- Use per-node span timings to find the dominant cost. Remedies in order: cache policy chunks ?
  confirm parallel fan-out → reduce RETRIEVAL_FETCH_K → small model for routing → trim prompt context ?
  drop the rerank call as a last resort.
- NEVER remove a guardrail, a citation requirement, or an escalation check to meet a budget.
- Report the per-category p50/p95/p99 table, not a single blended number.

**T30 — Frontend skeleton & API contract definition**
- FREEZE the contract in planning/14_FastAPI_Service_Setup_Plan.md. After this task, changes are additive
  only; breaking changes require /api/v2.
- Verify all five schema invariants in 14 —4 are enforced by validators.
- **React (Vite) auth-first UI:** LoginPage + SignupPage as only public routes; ProtectedRoute; minimal /app placeholder. See planning/19_React_Frontend_Plan.md.
- Optional: query skeleton that calls POST /api/v1/query and renders answer + citations + routing +
  escalation banner. No styling work, no auth UI — that is Sprints 8–9.

## NON-NEGOTIABLES
- Escalation is deterministic code, never a prompt instruction (ADR-007).
- Over-escalation is acceptable; under-escalation is a build failure.
- A refusal must never describe how the bypass could be performed.
- C4 never answers on partial evidence.
- Latency work never trades away safety.

## DEFINITION OF DONE
(a) Routing Accuracy >=95% with the confusion matrix published;
(b) Escalation Recall = 1.0 and Guardrail Effectiveness = 1.0, both CI-gated;
(c) per-category latency table within the ADR-010 budgets;
(d) eval/reports/sprint5/report.md committed with deltas;
(e) the API contract is frozen and the skeleton renders a real response;
(f) you state which of Tasks 24–30 are complete and paste the 16-SLO table.

Start by reading the Sprint 4 report and telling me which SLOs you expect to move and why.
````

---

## Prompt C — Sprint 6 Multi-Agent Orchestration
*Tasks 31–36 — full 7-agent reasoning — Gate 3: Prototype 2*

````
You are implementing **Sprint 6** of the Finance Risk & Investment Intelligence System capstone
(Tracker Tasks 31–36). Sprints 4 and 5 are complete: data layer, C1/C2/C3 paths, deterministic
E1—E8 escalation, guardrails at 1.0, routing >=95%, latency within the ADR-010 budgets, frozen API
contract.

## READ FIRST
1. planning/10_Detailed_Solution_Design.md    — agent contracts (§3), state write discipline (§2),
                                                the C4 sequence flow (§9.2), concurrency (§10)
2. planning/06_High_Level_Architecture.md      — the agent orchestration state diagram (§4) and the
                                                architectural invariants (§8)
3. planning/11_Query_Categories.md             — C4 definition, the C4-vs-C5 distinction, escalation
                                                — category matrix (§5)
4. planning/13_Prompt_Engineering_Framework.md — risk (§5), market data (§4.2), synthesis C4 structure (§6)
5. planning/09_Detailed_Use_Case_and_SLO.md    — UC-11 and UC-12 full flows including alternate flows
6. planning/12_Evaluation_Dataset_and_Test_Strategy.md — Sprint 6 trajectory (§5.3), pass criteria (§5.1)
7. eval/reports/sprint5/report.md               — current state

## SCOPE — Tasks 31 to 36

**T34 — Multi-agent / role orchestration working**
- Wire all 7 agents: Router, Retrieval, Market Data, Portfolio Evaluation, Risk, Synthesis, Escalation.
- Build the C4_HIGH_RISK subgraph per 06 —4: THREE-WAY parallel fan-out (Retrieval → Portfolio Eval ?
  Market Data) → Risk → deep Portfolio Evaluation → Synthesis, with escalation checks after every
  evidence-producing node.
- Implement the Market Data agent per 10 —3.4: interpret indicators ONLY through methodology retrieved
  from document 04, record source_chunk_id, and explicitly report absent indicator/region combinations.
  No general economic knowledge, no forecasting.
- Implement deep Portfolio Evaluation mode: implied post-change concentration when the query quantifies
  a change; all arithmetic in Python, never in the LLM.
- Enforce the state write discipline in 10 —2 — parallel branches write disjoint keys, reducers append.
- Verify true parallelism in traces. Confirm the invariants in 06 —8 still hold.

**T31 — Multi-step reasoning operational**
- Every C4 query must use >=2 agents and >=2 evidence types (10 —9.2 is the reference flow).
- Synthesis for C4 uses the exact structure in 13 —6: Question, Policy position, Current data, Market
  context, Risk assessment, What policy requires before such a decision, and the explicit
  non-recommendation line. NEVER a recommendation.
- Confidence is computed per 10 —3.6, not guessed, and is capped at 0.5 when any conflict is a breach.

**T32 — Hybrid reasoning consistency validation**
- Contradiction handling is the deliverable here (risk R7). When policy and data disagree, the answer
  must state BOTH with BOTH citations and never silently pick the comfortable reading.
- Verify severity assignment: breach (limit exceeded), warning (within 10%), info (definitional).
- Consistency test: run each C3/C4 query 3 times and assert the risk level, breach set, and escalation
  decision are identical every time. Nondeterminism in a risk verdict is a defect.
- Verify that the Risk agent discards any policy limit it cannot point at in a specific chunk.

**T33 — Dynamic tool selection stable**
- Template selection accuracy >=95% against golden `expected_query_ids` (10 —3.3, 13 —4.1).
- Verify the "no template fits" path returns an honest gap statement and never improvised SQL.
- Verify the single repair attempt on slot-validation failure, then graceful failure.

**T35 — Escalation & guardrails revalidated → both still 1.0 (HARD)**
- Re-run the full attack suite and the escalation recall suite AFTER the multi-agent changes. Added
  agents mean added paths for a trigger to be missed; this is the highest-risk regression in the project.
- Add C4-specific escalation tests: a trigger firing in the Market Data branch, a trigger firing in the
  deep Portfolio Evaluation stage, a fan-out branch failing (must escalate via E5, never answer).
- Confirm no answer is ever synthesized once escalation_required is true.

**T36 — Prototype 2**
- All 5 categories fully working end to end.
- Full eval run; commit eval/reports/sprint6/report.md.
- Sprint 6 targets: Faithfulness >=80%, Context Precision >=70%, Recall >=75%, Accuracy >=85%,
  SQL Correctness >=95%, Risk Classification >=95%, Judge >=80%, TSR ~85% and rising, all four hard
  gates still at their absolute values.
- Demo script: one query per category, including a C3 with a real breach and a C4 that escalates.

## NON-NEGOTIABLES
- C4 never answers on partial evidence — a failed fan-out branch means E5 and escalation.
- Synthesis still has no tools.
- Only the Risk agent assigns a risk level, and the deterministic classifier is authoritative.
- Escalation Recall and Guardrail Effectiveness must be 1.0 AFTER the changes, not before.
- C4 output is analysis, never a recommendation.
- Latency: C4 <=6s p95; C1/C2 must not regress past 2s.

## DEFINITION OF DONE
(a) all 7 agents wired with verified parallel fan-out;
(b) every C4 golden query uses >=2 agents and >=2 evidence types;
(c) 3-run consistency holds for risk level, breach set, and escalation decision on C3/C4;
(d) hard gates still 1.0 / 1.0 / 0 / <3%;
(e) eval/reports/sprint6/report.md committed with deltas from Sprint 5;
(f) Prototype 2 demo works for all 5 categories;
(g) you state which of Tasks 31–36 are complete and paste the 16-SLO table.

Start by reading the Sprint 5 report and naming the regression risk you will guard against first.
````

---

## Prompt D — Sprints 7–10 (brief kickoffs)

Sprints 7–10 are validation and hardening rather than new capability; short prompts suffice.

### Sprint 7 — Integration & Validation (Tasks 37–42)
````
Implement Sprint 7 (Tasks 37–42). Read planning/14_FastAPI_Service_Setup_Plan.md —10 (frontend field
mapping), planning/09_Detailed_Use_Case_and_SLO.md (all 16 SLOs), planning/12_..._Test_Strategy.md —4
(test levels), planning/07_ADR.md ADR-014 (RBAC enforcement point).
Deliver: frontend?backend integration against the frozen contract; all complex golden queries passing;
TSR improvement over Prototype 2 (target >=90%); SLO validation UNDER LOAD with per-category p95;
security validation (replay the whole golden set under analyst / risk_manager / compliance and diff —
RBAC violations must be 0); observability validation (every node spans, every metric increments, a past
request is fully reconstructable via /admin/traces/{trace_id}).
Commit eval/reports/sprint7/report.md. All 16 SLOs must now be measured, with the four hard gates green.
````

### Sprint 8 — Hardening (Tasks 43–48) — **most critical checkpoint**
````
Implement Sprint 8 (Tasks 43–48). Read planning/14_FastAPI_Service_Setup_Plan.md —5 (auth stub → JWT,
RBAC matrix), planning/07_ADR.md ADR-014 (consider adding Postgres RLS as defence in depth, as the ADR
defers), planning/05_Project_Setup_Readiness.md —2 (cost guardrail env vars).
Deliver: **signup + login** (`POST /auth/signup`, `POST /auth/login`), `users`/`sessions`/`turns` in **`finance_auth_db`**
(separate from vector/finance DB per ADR-020), JWT sessions;
admin PATCH to assign role/portfolios; RBAC enforced at the executor with the token scope
authoritative and non-overridable by request content; security review covering the 8 attack types plus
dependency and secret scanning; cost tracking with MAX_TOKENS_PER_REQUEST and DAILY_BUDGET_USD enforced;
load testing with per-category p95 held under sustained RPS; production readiness review against
Gate 4. Assert AUTH_MODE=stub is impossible when APP_ENV=prod.
Commit eval/reports/sprint8/report.md plus a load-test report and a security-review summary.
````

### Sprint 9 — Product Completion (Tasks 49–52)
````
Implement Sprint 9 (Tasks 49–52). Read planning/14_FastAPI_Service_Setup_Plan.md —8 (streaming) and —10
(field mapping), planning/13_Prompt_Engineering_Framework.md —7 (citation format for rendering),
planning/11_Query_Categories.md —5 (escalation — category).
Deliver: end-to-end query flow via the UI; clickable citations rendered from citations[] and a
"how was this answered" panel from routing; restricted-action UX — branch on `outcome`, hide every action
affordance for refused/escalated, show reviewer routing; streaming that stops token output immediately on
an escalation event and discards partial text; the disclaimer rendered on every response with no way to
suppress it. Prototype 3.
Commit eval/reports/sprint9/report.md.
````

### Sprint 10 — Release (Tasks 53–56)
````
Implement Sprint 10 (Tasks 53–56). Read planning/04_Evaluation_and_Measurement_Plan.md (cadence and
pass/fail rules), planning/09_Detailed_Use_Case_and_SLO.md Part B (the authoritative 16-SLO table),
planning/06_High_Level_Architecture.md —7 (deployment view).
Deliver: end-to-end integration testing across all 17 use cases; performance and scalability validation;
FINAL SLO EVALUATION against all 16 targets with the per-category latency table and the ADR-010 scope
qualifier stated explicitly; deployment and go-live.
Commit eval/reports/final/report.md as the submission artifact, with: the 16-SLO table (target, measured,
PASS/FAIL), the sprint-by-sprint trend for each SLO, the routing confusion matrix, the risk-classification
matrix, per-category latency percentiles, and an honest list of anything not met with the reason.
````

---

## Prompt E — Utility Prompts

### Debug a failing golden query
````
Golden query {{query_id}} is failing in eval/reports/{{sprint}}/report.md.
Read planning/12_Evaluation_Dataset_and_Test_Strategy.md —5.1 (per-query pass criteria) and
planning/10_Detailed_Solution_Design.md —7 (error handling).
1. Show me the record from eval/golden/golden_queries.jsonl.
2. Run the single query and show the trace: routing decision, evidence retrieved, escalation triggers
   evaluated, validator result.
3. Identify which of the 9 pass conditions failed and why.
4. Fix the ROOT CAUSE, not the symptom — if the bug is in a shared function, fix it there and check
   every caller. Do not special-case this query.
5. Add a regression test, re-run the full golden suite, and confirm no other SLO moved.
````

### Add a new SQL template
````
I need a query the current template registry cannot answer: {{description}}.
Read planning/10_Detailed_Solution_Design.md —5 (registry structure, executor rules) and
planning/07_ADR.md ADR-005 and ADR-014.
Add ONE template with: a stable query_id, description, tables, parameterized SQL with named slots, slot
validators (type/enum/range/nullability), and the correct `rbac_scoped` flag. Add a unit test for the
template and each validator, plus an integration test asserting the shape against the real database.
Confirm the rbac_scoped test still passes (every template touching portfolios, portfolio_holdings, or
investment_decisions must be scoped). Then re-run the golden suite.
````

### Tune a prompt
````
{{metric}} is at {{value}} against a target of {{target}}.
Read planning/13_Prompt_Engineering_Framework.md —9 (governance and A/B protocol).
Change exactly ONE prompt file. Bump its version header. Run the full golden set before and after and
show both 16-SLO tables. If the target metric improves but another regresses more than 3 points, revert.
Record the prompt version in the eval report header.
````

### Investigate an escalation miss (P0)
````
An escalation was missed: {{details}}. This is a P0 — Escalation Recall must be 1.0.
Follow the runbook in planning/05_Project_Setup_Readiness.md —5.5 exactly:
freeze the branch, pull the trace and identify which of E1—E8 should have fired, REPRODUCE AS A UNIT TEST
FIRST, fix the deterministic rule (per ADR-007, "improve the prompt" is never the sole remedy for an
escalation miss), add the case to the attack suite and the regression set permanently, then re-run both
the attack and golden suites.
````

---

> **Disclaimer.** Synthetic/educational data. Not investment advice.

---

## Prompt D+ — Production Grade & Cloud Readiness (use with Sprint 8 Gate 4 / Sprint 10)

```
You are hardening the Finance Risk & Investment Intelligence System for production and a future
cloud move. Do NOT rewrite agents. Follow planning/16_Production_and_Cloud_Readiness.md and
ADR-015, ADR-016, ADR-017, ADR-018 in planning/07_ADR.md.

Required outcomes:
1. Multi-stage Dockerfile; non-root; image tag finance-risk-api:<git-sha>; CMD is API only.
2. APP_ENV=prod refuses AUTH_MODE=stub and placeholder secrets.
3. app/core/storage.py CorpusStore Protocol + LocalCorpusStore; ingest uses it (S3 class stub OK).
4. deploy/compose.prod.yml (+ optional k8s stubs); DB is external URL; secrets from env.
5. /health and /health/ready (DB); stdout JSON logs; OTLP endpoint configurable.
6. Gate 4 checklist in 16 §6 ticked with evidence in eval/reports/ and a short PROD_READINESS.md.
7. Document cloud migration dry-run steps from 16 §7 (provider still TBD is fine).

Read also: planning/06_High_Level_Architecture.md §7, planning/05_Project_Setup_Readiness.md,
planning/14_FastAPI_Service_Setup_Plan.md.
```

---

## Prompt E — Stock Screening Feature

```
Add the Screener-like stock screening feature per planning/17_Stock_Screening_Feature.md and ADR-021.

1. In finance_risk_db: equity_universe + equity_fundamentals; seed ~500–2000 synthetic symbols.
2. Whitelist ScreenDefinition validator + parameterized SQL builder + POST /api/v1/screens/run.
3. GET /api/v1/screens/fields catalogue.
4. Later: from-nl agent; saved_screens in finance_auth_db; UI builder (Sprint 9).
5. Never scrape screener.in; always non-advice disclaimer + SQL citation.
```

---

## Prompt F — removed from capstone track

Production work uses **`planning/production/MASTER_PROMPT.md`** only.
Do not run production phases inside capstone sprints.

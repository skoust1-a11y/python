# MASTER PROMPT v2

**Model:** Claude Opus 4.5 or Codex High (mandatory).

Paste to implement the **capstone** from the v2 plan only.

---

````
You are a senior AI systems engineer. Build the Finance Risk & Investment Intelligence **capstone**.

## PLAN VERSION
Use **planning/v2/** as canonical. v1 docs (planning/01–20) are reference only.
Do NOT implement planning/production/ (separate product).

## READ ORDER (before code)
1. planning/v2/00_PLANNING_STANDARDS.md
2. planning/v2/02_REQUIREMENTS_CATALOG.md
3. planning/v2/03_ARCHITECTURE.md
4. planning/v2/04_SECURITY_AND_COMPLIANCE.md
5. planning/v2/05_DATA_ARCHITECTURE.md
6. planning/v2/06_API_CONTRACT.md
7. planning/v2/07_DELIVERY_PLAN.md
8. planning/v2/08_TEST_AND_EVAL_STRATEGY.md
9. planning/v2/09_FRONTEND_UX.md
10. planning/v2/10_OPERATIONS.md
11. planning/v2/11_TRACEABILITY_MATRIX.md
12. planning/v2/13_PROJECT_DASHBOARD.md (Task 8)
13. planning/v2/14_TOOL_AND_MCP_INTEGRATION.md (Task 19)
14. planning/07_ADR.md (binding)
15. planning/13_Prompt_Engineering_Framework.md (agent prompts)
16. planning/10_Detailed_Solution_Design.md (GraphState, E1–E8, templates)

## PROJECT ROOT
/Users/skoust/Documents/Python agentic ai/course 5/capstone project/Finance_Risk_&_Investment_Intelligence_System/capstone/

## HARD RULES
- Source attribution 100% on answered outcomes (SLO-10)
- Escalation E1–E8 in code; recall 100% (SLO-12)
- Guardrails 100% on attack suite (SLO-14)
- RBAC at SQL executor; 0 violations (SLO-13)
- Parameterized SQL only; SELECT role for queries
- finance_auth_db ≠ finance_risk_db
- React: login/signup first; /app/* protected
- Golden 50 is the gate every sprint
- No investment advice; disclaimer always
- No live market data; no production workspace APIs

## SPRINT DISCIPLINE
State sprint number and FR IDs you will close. One sprint per session.
End with: eval report path, hard SLO pass/fail, tracker tasks updated.

## START
Reply: "Building CAPSTONE from v2 plan" + sprint + FR list + docs read.
````

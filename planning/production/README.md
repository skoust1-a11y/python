# Production Plan (separate product)

**Not part of the graded capstone.** Do not mix this work into capstone sprints or golden-set gates.

Capstone plan: [`../capstone/`](../capstone/) (code) · [`../planning/capstone/`](../planning/capstone/) (plan).

| Doc | Purpose |
|---|---|
| [`MASTER_PROMPT.md`](MASTER_PROMPT.md) | Agent prompt for **production** build only |
| [`01_Product_and_Scope.md`](01_Product_and_Scope.md) | Vision, boundaries, legal posture |
| [`02_User_Owned_Data_Model.md`](02_User_Owned_Data_Model.md) | Portfolios, strategy docs, risk/valuation metrics |
| [`03_Realtime_Market_Data.md`](03_Realtime_Market_Data.md) | Quotes + news adapters; per-query `corpus` / `current` switch |
| [`04_Architecture_and_APIs.md`](04_Architecture_and_APIs.md) | Services, APIs, DB layout |
| [`05_Roadmap.md`](05_Roadmap.md) | Phased delivery P1–P5 |
| [`06_SLOs_and_Compliance.md`](06_SLOs_and_Compliance.md) | Production SLOs |

## Relationship to capstone
- May **reuse ideas** (agents, citations, guardrails, screening engine).
- Is a **separate plan and deployable** — not `APP_MODE` flip inside the graded project.
- Capstone repo can stay frozen for submission while production lives in its own service/repo later.

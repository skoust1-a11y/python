# 18 � Capstone and Production are SEPARATE plans and codebases

They are **not** one app with an `APP_MODE` switch for planning/delivery.

| Track | Code | Planning | Graded? |
|---|---|---|---|
| **Capstone** | [`../capstone/`](../capstone/) | [`capstone/`](capstone/) | Yes � tracker & golden 50 |
| **Production** | [`../production/`](../production/) | [`production/`](production/) | No � separate product plan |

## How to use
- Building the course project ? work in **`../capstone/`**; agent prompt: **`capstone/MASTER_PROMPT.md`**.
- Building the real user-owned + real-time system ? work in **`../production/`**; agent prompt: **`production/MASTER_PROMPT.md`**.
- Do not mix Prompt F / workspace APIs into capstone sprints.

## Shared ideas (documentation only)
Citations, guardrails, auth?vector DB, screening **engine** concepts may be reused later in production.
That reuse is intentional copying of patterns � **not** a combined delivery plan.

ADR-022 records this separation.

## Per-query evidence switch (not `APP_MODE`)

Users may pick **Documents only** (`corpus`) or **Documents + current** (`current` = live quotes + news) on each query. That is a request option, not a delivery-track flip.

- Capstone: `CURRENT_FACTORS_ENABLED=false`; default `corpus`; `current` ? 409.
- Production: toggle enabled after providers are connected; same agents, extra adapter evidence.
- Golden set always uses `corpus`.

Contract: `14_FastAPI_Service_Setup_Plan.md` �3.6 � adapters: `production/03_Realtime_Market_Data.md`.

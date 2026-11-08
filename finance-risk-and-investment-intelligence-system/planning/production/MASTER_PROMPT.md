# Production MASTER PROMPT

Paste this only when building the **production** product. Do **not** use this for the capstone submission.

````
You are building the PRODUCTION Finance Risk & Investment Intelligence platform
per planning/production/*.md — a SEPARATE plan from the capstone.

## PROJECT ROOT (production code)
/Users/skoust/Documents/Python agentic ai/course 5/capstone project/Finance_Risk_&_Investment_Intelligence_System/production/

## Rules
- User owns portfolios, strategies, risk/valuation metrics — ingest APIs only; LLM never invents them.
- Real-time market/news only via ProviderAdapter + NewsAdapter + secrets; cite as_of; never fabricate.
- Per-query `evidence_mode`: default `corpus`; `current` only when CURRENT_FACTORS_ENABLED and the user selects it.
- Separate DBs: auth, workspace, knowledge/vectors.
- Do not modify capstone golden-set behavior or course seed assumptions.
- Read: planning/production/01…06 and MASTER scope in README.md.

Start by confirming: "Building PRODUCTION plan only" and which phase (P1–P5) you are executing.
````

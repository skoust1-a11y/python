# 20 — AI Agent Model Policy (Cursor / planning / implementation)

**Which model to use when *you* (the human) drive the agent — not the runtime LLM inside the product (see ADR-004).**

---

## Required models

| Activity | Model (pick one) | Where in Cursor |
|---|---|---|
| **Planning** (Sprints 1–3, ADRs, architecture, new feature specs) | **Claude Opus 4.5** (preferred) **or Codex High** | Agent chat / Composer — set model before starting |
| **Implementation** (Sprints 4–10, refactors, eval fixes) | **Claude Opus 4.5** **or Codex High** | Same |
| **Quick edits** (typos, one-file tweak) | Any fast model OK | Optional downgrade |

Do **not** use small/fast models for:
- Multi-agent orchestration design
- Guardrail / escalation logic
- Golden-set or SLO changes
- Auth + RBAC + React auth-gate wiring

---

## How to start a session

1. Select **Claude Opus 4.5** or **Codex High** in Cursor.
2. Paste from [`00_MASTER_PROMPT.md`](00_MASTER_PROMPT.md) or [`capstone/MASTER_PROMPT.md`](capstone/MASTER_PROMPT.md).
3. Add the sprint prompt from [`15_COMPLETION_PROMPTS.md`](15_COMPLETION_PROMPTS.md) (A–E for capstone).
4. First line of agent reply must confirm model tier and sprint tasks.

---

## Subagents / long tasks

When using Cursor **Task** or background agents for planning or large implementation:
- Request **Claude Opus 4.5** or **Codex High** explicitly in the task description.
- Do not delegate architecture or safety rules to a fast model.

---

## Not in scope (product runtime)

The **application** LLM (router, agents, synthesis) stays per **ADR-004**:
- `gpt-4o-mini` (router), `gpt-4o` (agents/judge), or OpenAI-compatible equivalent.
- That is unrelated to which Cursor model writes the Python/React code.

---

## Changelog

| Version | Note |
|---|---|
| 1.0 | Opus 4.5 / Codex High mandated for planning + implementation |

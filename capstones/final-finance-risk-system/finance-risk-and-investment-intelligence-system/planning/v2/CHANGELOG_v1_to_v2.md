# Changelog: v1 → v2

## Why v2

v1 grew organically (20+ files, encoding issues, duplicated ADR prose, weak traceability). v2 applies engineering documentation standards.

## Improvements

| Area | v1 | v2 |
|---|---|---|
| Structure | Flat numbered files | Layered: exec → reqs → arch → delivery → ops |
| Requirements | Scattered in use cases | Catalog with FR/NFR/SR IDs + MoSCoW |
| Traceability | Implicit | Matrix `11_TRACEABILITY_MATRIX.md` |
| Standards | Ad hoc | RFC 2119, DoR/DoD, single source of truth |
| Architecture | Long narrative | C4 L1–L2 + invariants + links to detail |
| API | 430-line monolith | v2 summary + v1 detail reference |
| Frontend | Added late in doc 19 | Integrated UX requirements + routes |
| Encoding | Broken characters (�) | Clean UTF-8 |
| Agent prompt | Long mixed prompt | Focused `MASTER_PROMPT_v2.md` |
| Production | Mixed into capstone | Explicitly separate (`../production/`) |

## What to use

| Task | Document |
|---|---|
| Review / sign-off | `v2/README.md` + `01_EXECUTIVE_SUMMARY.md` |
| Implementation | `v2/MASTER_PROMPT_v2.md` |
| Deep dive (prompts, E1–E8, OpenAPI fields) | v1 `10`, `13`, `14` as reference |

## Migration

- **Do not delete v1** — prompts and schemas remain useful.
- **New work:** edit v2 first; sync v1 only if graders require legacy doc numbers.
- GATE-1 sign-off should reference **v2**.

# Implementation evidence pack

| # | Deliverable | Artifact |
|---|---|---|
| 1 | Ruff | `ruff.txt` — `ruff check app tests` clean |
| 2 | Testcases | `pytest.txt` — `tests/test_api.py`, `tests/test_guardrails.py` |
| 3 | ER diagram | [`../diagrams/ER_Diagram.html`](../diagrams/ER_Diagram.html) |
| 4 | Prompts | `capstone/app/prompts/` (7 agents + 3 refusals). Spec: `planning/13_Prompt_Engineering_Framework.md` |
| 5 | Logs verified | `logs.jsonl` — structlog JSON `http_request` lines |
| 6 | Backend endpoints | `ENDPOINTS.md` vs `planning/v2/06_API_CONTRACT.md`. Procedure: `ENDPOINT_VERIFICATION_PROCEDURE.md` |
| 7 | AI validation of diagrams | `Task6_AI_Diagram_Validation.md` |

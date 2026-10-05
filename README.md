# Finance Risk & Investment Intelligence System

Agentic AI capstone. An agentic RAG + SQL assistant that answers portfolio, risk and policy questions over the course dataset and 7 policy PDFs, with guardrails, escalation and an SLO-gated evaluation suite.

> Synthetic/educational data. Not investment advice.

## Folder layout

| Folder | What is in it |
|---|---|
| [`presentation/`](presentation/) | Everything for the review: slides, final report, diagrams, spreadsheets |
| [`capstone/`](capstone/) | Application: FastAPI backend (`app/`), React frontend (`frontend/`), eval suite (`eval/`), tests, course PDFs (`Documents/`) |
| [`planning/`](planning/) | Sprint task documents (`00`–`20`), v2 plan and gate sign-offs (`v2/`), sprint PDFs, diagrams, evidence |
| [`docs/`](docs/) | System architecture, database architecture, table reference, libraries |
| [`deploy/`](deploy/) | Dockerfile, production compose, Kubernetes manifests, deploy guide (`render.yaml` at root) |

## Presentation pack

| File | Path |
|---|---|
| Final presentation (Keynote, 16 slides) | [`presentation/01_slides/FRIIS_Final_Presentation.key`](presentation/01_slides/FRIIS_Final_Presentation.key) |
| Project presentation (PowerPoint, 19 slides) | [`presentation/01_slides/Project_Presentation.pptx`](presentation/01_slides/Project_Presentation.pptx) |
| REST API endpoints slide | [`REST_API_Endpoints.key`](presentation/01_slides/REST_API_Endpoints.key) / [`REST_API_Endpoints_Slide.pptx`](presentation/01_slides/REST_API_Endpoints_Slide.pptx) |
| Final report | [`presentation/02_report/FRIIS_Final_Report.docx`](presentation/02_report/FRIIS_Final_Report.docx) |
| Architecture, workflow, ER, API diagrams | [`presentation/03_diagrams/`](presentation/03_diagrams/) |
| Evaluation spreadsheets (SLO history, human eval, API tests, policy questions, confidence demo) | [`presentation/04_spreadsheets/evaluation/`](presentation/04_spreadsheets/evaluation/) |
| Project tracker, libraries inventory | [`presentation/04_spreadsheets/project_management/`](presentation/04_spreadsheets/project_management/) |

## Evidence

| Artifact | Path |
|---|---|
| SLO report (strict re-score, 2 Oct, 13/16) | [`capstone/eval/reports/final/report.md`](capstone/eval/reports/final/report.md) |
| Held-out questions report | [`capstone/eval/reports/holdout/report.md`](capstone/eval/reports/holdout/report.md) |
| Course compliance checklist | [`planning/deliverables/evidence/COURSE_COMPLIANCE.md`](planning/deliverables/evidence/COURSE_COMPLIANCE.md) |
| Gate sign-offs | [`planning/v2/GATE_6_SIGNOFF.md`](planning/v2/GATE_6_SIGNOFF.md) (also GATE-1…5) |
| Project board | [`planning/deliverables/dashboard/index.html`](planning/deliverables/dashboard/index.html) |

## Quick start

Needs Python 3.9+ (Docker image uses 3.11), Node 18+ and Postgres on `localhost:5432`. Full steps in [`capstone/README.md`](capstone/README.md).

```bash
cd capstone
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add an LLM API key
python -m app.sqlq.seed --reset
uvicorn app.main:app --reload --port 8000   # API docs: http://localhost:8000/docs

cd frontend && npm install && npm run dev   # UI: http://localhost:5173 (analyst@local / Password123)
```

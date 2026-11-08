import {
  Button,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Divider,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Select,
  Stack,
  Stat,
  Text,
  colorPalette,
  computeDAGLayout,
  useEffect,
  useHostTheme,
  useMemo,
  useState,
} from "cursor/canvas";

type FlowId =
  | "ctx"
  | "arch"
  | "bands"
  | "orch"
  | "c1"
  | "c2"
  | "c3"
  | "c4"
  | "c5"
  | "ingest"
  | "guard";

type FlowNode = {
  id: string;
  label: string;
  kind: "boundary" | "route" | "agent" | "store" | "safety" | "out";
};

type FlowDef = {
  id: FlowId;
  title: string;
  subtitle: string;
  budget: string;
  nodes: FlowNode[];
  edges: Array<{ from: string; to: string }>;
  steps: Array<{ active: string[]; note: string }>;
};

const FLOWS: FlowDef[] = [
  {
    id: "ctx",
    title: "System Context (C4 L1)",
    subtitle: "Actors, the system, evidence stores, LLM, human handoff, observability",
    budget: "architecture",
    nodes: [
      { id: "p1", label: "Investment Analyst", kind: "boundary" },
      { id: "p2", label: "Risk Manager", kind: "boundary" },
      { id: "p3", label: "Portfolio Manager", kind: "boundary" },
      { id: "p4", label: "Compliance", kind: "boundary" },
      { id: "p5", label: "Platform Admin", kind: "boundary" },
      { id: "sys", label: "Finance Risk System", kind: "route" },
      { id: "pdf", label: "Policy Corpus (7 PDFs)", kind: "store" },
      { id: "db", label: "finance_risk_db", kind: "store" },
      { id: "llm", label: "OpenAI-compatible LLM", kind: "agent" },
      { id: "hum", label: "Human Analyst Queue", kind: "safety" },
      { id: "obs", label: "Observability", kind: "out" },
    ],
    edges: [
      { from: "p1", to: "sys" },
      { from: "p2", to: "sys" },
      { from: "p3", to: "sys" },
      { from: "p4", to: "sys" },
      { from: "p5", to: "sys" },
      { from: "sys", to: "pdf" },
      { from: "sys", to: "db" },
      { from: "sys", to: "llm" },
      { from: "llm", to: "sys" },
      { from: "sys", to: "hum" },
      { from: "sys", to: "obs" },
    ],
    steps: [
      {
        active: ["p1", "p2", "p3", "p4"],
        note: "Internal personas query the system: analyst, risk, PM, compliance (not retail clients).",
      },
      {
        active: ["p5", "sys"],
        note: "Platform Admin uses /admin, health, traces — no answer-path privilege.",
      },
      {
        active: ["sys", "pdf"],
        note: "Semantic retrieval over 7 policy PDFs (strategy ? Basel III ? risk framework).",
      },
      {
        active: ["sys", "db"],
        note: "Read-only parameterized SQL against portfolios, holdings, risk logs, markets, decisions.",
      },
      {
        active: ["sys", "llm"],
        note: "Tiered LLM: router (cheap), agents (reasoning), judge (eval) — OpenAI-compatible.",
      },
      {
        active: ["sys", "hum"],
        note: "Mandatory escalation with full context whenever E1–E8 fires — Escalation Recall = 1.0.",
      },
      {
        active: ["sys", "obs"],
        note: "Every request: structlog + OTel spans + Prometheus + token/cost meter.",
      },
    ],
  },
  {
    id: "arch",
    title: "Architecture Flow (C4 L2)",
    subtitle: "Request path through FastAPI ? safety ? router ? LangGraph ? RAG/SQL ? synthesis",
    budget: "layers L1–L6",
    nodes: [
      { id: "client", label: "API Client", kind: "boundary" },
      { id: "api", label: "L1 FastAPI /query", kind: "boundary" },
      { id: "auth", label: "Auth + RBAC", kind: "boundary" },
      { id: "gin", label: "X1 Input Guardrail", kind: "safety" },
      { id: "rt", label: "L2 Router Agent", kind: "route" },
      { id: "graph", label: "L3 LangGraph", kind: "route" },
      { id: "retr", label: "L4 Retrieval", kind: "agent" },
      { id: "hyb", label: "Hybrid retriever", kind: "agent" },
      { id: "vs", label: "pgvector", kind: "store" },
      { id: "pev", label: "L5 Portfolio Eval", kind: "agent" },
      { id: "mda", label: "L5 Market Data", kind: "agent" },
      { id: "rsk", label: "L5 Risk Agent", kind: "agent" },
      { id: "tpl", label: "SQL templates", kind: "store" },
      { id: "db", label: "finance_risk_db", kind: "store" },
      { id: "esc", label: "X1 Escalation E1–E8", kind: "safety" },
      { id: "syn", label: "L6 Synthesis", kind: "agent" },
      { id: "cit", label: "Citation formatter", kind: "out" },
      { id: "gout", label: "X1 Output validator", kind: "safety" },
      { id: "mem", label: "Session memory", kind: "store" },
      { id: "obs", label: "X2 Observability", kind: "out" },
    ],
    edges: [
      { from: "client", to: "api" },
      { from: "api", to: "auth" },
      { from: "auth", to: "gin" },
      { from: "gin", to: "rt" },
      { from: "rt", to: "graph" },
      { from: "graph", to: "retr" },
      { from: "retr", to: "hyb" },
      { from: "hyb", to: "vs" },
      { from: "graph", to: "pev" },
      { from: "graph", to: "mda" },
      { from: "graph", to: "rsk" },
      { from: "pev", to: "tpl" },
      { from: "mda", to: "tpl" },
      { from: "rsk", to: "tpl" },
      { from: "tpl", to: "db" },
      { from: "graph", to: "esc" },
      { from: "graph", to: "syn" },
      { from: "syn", to: "cit" },
      { from: "cit", to: "gout" },
      { from: "esc", to: "gout" },
      { from: "gout", to: "api" },
      { from: "graph", to: "mem" },
      { from: "graph", to: "obs" },
    ],
    steps: [
      {
        active: ["client", "api", "auth"],
        note: "L1 Query Interface: POST /api/v1/query — JWT ? role + allowed_portfolio_ids + trace_id.",
      },
      {
        active: ["gin"],
        note: "X1 Safety first: input guardrail blocks override / bypass / injection before any LLM spend.",
      },
      {
        active: ["rt"],
        note: "L2 Understanding: Router assigns C1–C5, risk_level, entities, and path.",
      },
      {
        active: ["graph"],
        note: "L3 Orchestration: LangGraph state machine — conditional edges, budgets, retries.",
      },
      {
        active: ["retr", "hyb", "vs"],
        note: "L4 Knowledge: hybrid vector + BM25 + rerank over policy_chunks.",
      },
      {
        active: ["pev", "mda", "rsk", "tpl", "db"],
        note: "L5 Data Analysis: named SQL templates ? read-only executor ? finance_risk_db.",
      },
      {
        active: ["esc"],
        note: "X1 Escalation engine runs after evidence nodes — any E2–E8 ? terminal handoff.",
      },
      {
        active: ["syn", "cit", "gout", "api"],
        note: "L6 Synthesis is tool-less; citations formatted; output validator; response returned.",
      },
      {
        active: ["mem", "obs"],
        note: "Cross-cutting: session memory (last N turns) + logs/traces/metrics/cost on every node.",
      },
    ],
  },
  {
    id: "bands",
    title: "System Flow — Four Bands",
    subtitle: "Narrative request journey: Boundary ? Understanding ? Execution ? Synthesis",
    budget: "end-to-end",
    nodes: [
      { id: "b1a", label: "Authenticate", kind: "boundary" },
      { id: "b1b", label: "Input guardrail", kind: "safety" },
      { id: "b2a", label: "Classify category", kind: "route" },
      { id: "b2b", label: "Extract entities", kind: "route" },
      { id: "b3a", label: "Fan-out agents", kind: "agent" },
      { id: "b3b", label: "Evidence bundle", kind: "store" },
      { id: "b3c", label: "Risk + E1–E8", kind: "safety" },
      { id: "b4a", label: "Synthesis", kind: "agent" },
      { id: "b4b", label: "Validate output", kind: "safety" },
      { id: "b4c", label: "Response envelope", kind: "out" },
    ],
    edges: [
      { from: "b1a", to: "b1b" },
      { from: "b1b", to: "b2a" },
      { from: "b2a", to: "b2b" },
      { from: "b2b", to: "b3a" },
      { from: "b3a", to: "b3b" },
      { from: "b3b", to: "b3c" },
      { from: "b3c", to: "b4a" },
      { from: "b3c", to: "b4b" },
      { from: "b4a", to: "b4b" },
      { from: "b4b", to: "b4c" },
    ],
    steps: [
      {
        active: ["b1a", "b1b"],
        note: "Band 1 — Boundary: auth + RBAC scope; guardrail before any expensive model call.",
      },
      {
        active: ["b2a", "b2b"],
        note: "Band 2 — Understanding: category (C1–C5) + entities. Routing Accuracy SLO >=95%.",
      },
      {
        active: ["b3a", "b3b"],
        note: "Band 3 — Execution: path-conditional depth; agents write typed evidence only (no free chat).",
      },
      {
        active: ["b3c"],
        note: "Still Band 3: Risk assigns level; deterministic escalation can divert to terminal handoff.",
      },
      {
        active: ["b4a"],
        note: "Band 4 — Synthesis: no tools; may only assert what is in the evidence bundle.",
      },
      {
        active: ["b4b", "b4c"],
        note: "Output validator: citations, no advice, disclaimer ? response envelope + trace_id.",
      },
    ],
  },
  {
    id: "orch",
    title: "Orchestration State Machine",
    subtitle: "LangGraph: guardrail ? router ? path ? escalation check ? synthesis / handoff",
    budget: "LangGraph",
    nodes: [
      { id: "gin", label: "Input Guardrail", kind: "safety" },
      { id: "rt", label: "Router", kind: "route" },
      { id: "c1", label: "C1 RAG path", kind: "agent" },
      { id: "c2", label: "C2 SQL path", kind: "agent" },
      { id: "c3", label: "C3 Hybrid fan-out", kind: "agent" },
      { id: "c4", label: "C4 High-Risk fan-out", kind: "agent" },
      { id: "c5", label: "C5 Escalation", kind: "safety" },
      { id: "chk", label: "Escalation check", kind: "safety" },
      { id: "weak", label: "Insufficient evidence", kind: "out" },
      { id: "syn", label: "Synthesis", kind: "agent" },
      { id: "esc", label: "Escalation terminal", kind: "safety" },
      { id: "ov", label: "Output validator", kind: "safety" },
      { id: "done", label: "Emit response", kind: "out" },
    ],
    edges: [
      { from: "gin", to: "rt" },
      { from: "gin", to: "esc" },
      { from: "rt", to: "c1" },
      { from: "rt", to: "c2" },
      { from: "rt", to: "c3" },
      { from: "rt", to: "c4" },
      { from: "rt", to: "c5" },
      { from: "c1", to: "chk" },
      { from: "c2", to: "chk" },
      { from: "c3", to: "chk" },
      { from: "c4", to: "chk" },
      { from: "c5", to: "esc" },
      { from: "chk", to: "syn" },
      { from: "chk", to: "esc" },
      { from: "chk", to: "weak" },
      { from: "syn", to: "ov" },
      { from: "weak", to: "ov" },
      { from: "esc", to: "ov" },
      { from: "ov", to: "done" },
      { from: "ov", to: "syn" },
    ],
    steps: [
      {
        active: ["gin"],
        note: "Entry: override/bypass/injection -> Escalation (E1). Clean -> Router.",
      },
      {
        active: ["rt"],
        note: "Router picks exactly one path: C1, C2, C3, C4, or C5.",
      },
      {
        active: ["c1", "c2"],
        note: "Fast paths: C1 Retrieval only · C2 Portfolio/SQL only (<=2s budget).",
      },
      {
        active: ["c3", "c4"],
        note: "Deep paths: C3 parallel RAG+SQL ? Risk · C4 adds Market + deep Portfolio Eval.",
      },
      {
        active: ["c5", "esc"],
        note: "C5 (or E1 from guardrail): terminal Escalation — no autonomous answer.",
      },
      {
        active: ["chk"],
        note: "After evidence: E2–E8 may divert; E5 ? insufficient-evidence template.",
      },
      {
        active: ["syn", "ov", "done"],
        note: "Clear ? Synthesis ? validator (1 citation retry allowed) ? response emitted.",
      },
    ],
  },
  {
    id: "c1",
    title: "C1 — Policy Interpretation (RAG)",
    subtitle: "Single-hop: Router -> Retrieval -> Synthesis",
    budget: "<=2s p95",
    nodes: [
      { id: "req", label: "Request", kind: "boundary" },
      { id: "auth", label: "Auth / RBAC", kind: "boundary" },
      { id: "gin", label: "Input Guardrail", kind: "safety" },
      { id: "router", label: "Router -> C1", kind: "route" },
      { id: "retr", label: "Retrieval", kind: "agent" },
      { id: "vec", label: "pgvector", kind: "store" },
      { id: "esc", label: "Escalation check", kind: "safety" },
      { id: "syn", label: "Synthesis", kind: "agent" },
      { id: "ov", label: "Output validator", kind: "safety" },
      { id: "resp", label: "Response + citations", kind: "out" },
    ],
    edges: [
      { from: "req", to: "auth" },
      { from: "auth", to: "gin" },
      { from: "gin", to: "router" },
      { from: "router", to: "retr" },
      { from: "retr", to: "vec" },
      { from: "vec", to: "retr" },
      { from: "retr", to: "esc" },
      { from: "esc", to: "syn" },
      { from: "syn", to: "ov" },
      { from: "ov", to: "resp" },
    ],
    steps: [
      { active: ["req"], note: "Analyst submits a policy question with JWT." },
      { active: ["auth"], note: "Role + allowed_portfolio_ids attached; trace_id stamped." },
      { active: ["gin"], note: "Deterministic + LLM guardrail screens override/bypass intent." },
      { active: ["router"], note: "Router classifies category=C1 (Investment Policy Interpretation)." },
      { active: ["retr", "vec"], note: "Hybrid retrieval over 7 policy PDFs with page/section metadata." },
      { active: ["esc"], note: "E1–E8 evaluated on evidence (usually clear for pure C1)." },
      { active: ["syn"], note: "Tool-less Synthesis composes answer from doc_evidence only." },
      { active: ["ov", "resp"], note: "Citations validated; disclaimer attached; Source Attribution = 1.0." },
    ],
  },
  {
    id: "c2",
    title: "C2 — Portfolio & Risk Lookup (SQL)",
    subtitle: "Router -> SQL templates -> Synthesis",
    budget: "<=2s p95",
    nodes: [
      { id: "req", label: "Request", kind: "boundary" },
      { id: "gin", label: "Input Guardrail", kind: "safety" },
      { id: "router", label: "Router -> C2", kind: "route" },
      { id: "pe", label: "Portfolio Eval", kind: "agent" },
      { id: "tpl", label: "SQL templates", kind: "store" },
      { id: "db", label: "finance_risk_db", kind: "store" },
      { id: "esc", label: "Escalation check", kind: "safety" },
      { id: "syn", label: "Synthesis", kind: "agent" },
      { id: "resp", label: "Response + SQL cites", kind: "out" },
    ],
    edges: [
      { from: "req", to: "gin" },
      { from: "gin", to: "router" },
      { from: "router", to: "pe" },
      { from: "pe", to: "tpl" },
      { from: "tpl", to: "db" },
      { from: "db", to: "pe" },
      { from: "pe", to: "esc" },
      { from: "esc", to: "syn" },
      { from: "syn", to: "resp" },
    ],
    steps: [
      { active: ["req"], note: "Structured lookup: holdings, risk logs, decisions, indicators." },
      { active: ["gin"], note: "Guardrail: no override intent." },
      { active: ["router"], note: "Router -> C2; entities extracted (portfolio, threshold, sector)." },
      { active: ["pe", "tpl", "db"], note: "Named parameterized template; SELECT-only role; RBAC filter." },
      { active: ["esc"], note: "If escalation_flag rows appear, divert to Escalation (E2)." },
      { active: ["syn", "resp"], note: "Answer cites query_id + result set; SQL Correctness target >=95%." },
    ],
  },
  {
    id: "c3",
    title: "C3 — Hybrid Risk Evaluation",
    subtitle: "Parallel RAG + SQL ? Risk ? Synthesis / Escalation",
    budget: "<=4s p95",
    nodes: [
      { id: "req", label: "Request", kind: "boundary" },
      { id: "router", label: "Router -> C3", kind: "route" },
      { id: "retr", label: "Retrieval", kind: "agent" },
      { id: "pe", label: "Portfolio Eval", kind: "agent" },
      { id: "vec", label: "pgvector", kind: "store" },
      { id: "db", label: "finance_risk_db", kind: "store" },
      { id: "risk", label: "Risk Agent", kind: "agent" },
      { id: "esc", label: "E1–E8 engine", kind: "safety" },
      { id: "syn", label: "Synthesis", kind: "agent" },
      { id: "hand", label: "Human handoff", kind: "safety" },
      { id: "resp", label: "Dual-cite answer", kind: "out" },
    ],
    edges: [
      { from: "req", to: "router" },
      { from: "router", to: "retr" },
      { from: "router", to: "pe" },
      { from: "retr", to: "vec" },
      { from: "pe", to: "db" },
      { from: "retr", to: "risk" },
      { from: "pe", to: "risk" },
      { from: "risk", to: "esc" },
      { from: "esc", to: "syn" },
      { from: "esc", to: "hand" },
      { from: "syn", to: "resp" },
      { from: "hand", to: "resp" },
    ],
    steps: [
      { active: ["req"], note: "Example: Are any assets exceeding allowed risk thresholds?" },
      { active: ["router"], note: "Category=C3 Hybrid; entities include threshold + portfolio scope." },
      {
        active: ["retr", "pe", "vec", "db"],
        note: "Fan-out in parallel: policy limits from PDFs + risk_logs/holdings from SQL.",
      },
      {
        active: ["risk"],
        note: "Risk reconciles policy thresholds vs observed risk_score (Low/Med/High).",
      },
      {
        active: ["esc"],
        note: "If escalation_flag=TRUE or limit breach ? E2/E6 fire (terminal).",
      },
      {
        active: ["hand", "resp"],
        note: "Escalated path: handoff envelope, no autonomous answer.",
      },
      {
        active: ["syn", "resp"],
        note: "Clear path: Synthesis with DOC: + SQL: citations and contradiction notes.",
      },
    ],
  },
  {
    id: "c4",
    title: "C4 — High-Risk Decision",
    subtitle: "3-way fan-out ? Risk ? deep Portfolio Eval",
    budget: "<=6s p95",
    nodes: [
      { id: "req", label: "Request", kind: "boundary" },
      { id: "gin", label: "Guardrail", kind: "safety" },
      { id: "router", label: "Router -> C4", kind: "route" },
      { id: "retr", label: "Retrieval", kind: "agent" },
      { id: "pe", label: "Portfolio Eval", kind: "agent" },
      { id: "mkt", label: "Market Data", kind: "agent" },
      { id: "risk", label: "Risk Agent", kind: "agent" },
      { id: "deep", label: "Deep Portfolio Eval", kind: "agent" },
      { id: "esc", label: "Escalation check", kind: "safety" },
      { id: "syn", label: "Synthesis", kind: "agent" },
      { id: "resp", label: "Answer or escalate", kind: "out" },
    ],
    edges: [
      { from: "req", to: "gin" },
      { from: "gin", to: "router" },
      { from: "router", to: "retr" },
      { from: "router", to: "pe" },
      { from: "router", to: "mkt" },
      { from: "retr", to: "risk" },
      { from: "pe", to: "risk" },
      { from: "mkt", to: "risk" },
      { from: "risk", to: "deep" },
      { from: "deep", to: "esc" },
      { from: "esc", to: "syn" },
      { from: "syn", to: "resp" },
    ],
    steps: [
      { active: ["req", "gin"], note: "High-stakes ask screened first — override intent ? C5/E1 immediately." },
      { active: ["router"], note: "Router -> C4 High-Risk Financial Decision." },
      {
        active: ["retr", "pe", "mkt"],
        note: "Parallel fan-out: policy + portfolio/SQL + market indicators.",
      },
      { active: ["risk"], note: "Risk agent assigns level; flags breaches and stale assessments." },
      { active: ["deep"], note: "Deep portfolio eval: concentration, benchmark, decision history." },
      { active: ["esc"], note: "Any E2–E8 trigger pre-empts synthesis." },
      { active: ["syn", "resp"], note: "If clear: grounded multi-source answer with risk summary." },
    ],
  },
  {
    id: "c5",
    title: "C5 — Escalation / Override",
    subtitle: "Terminal handoff — no autonomous answer",
    budget: "<=1.5s p95",
    nodes: [
      { id: "req", label: "Override request", kind: "boundary" },
      { id: "gin", label: "Input Guardrail", kind: "safety" },
      { id: "e1", label: "E1 Override intent", kind: "safety" },
      { id: "esc", label: "Escalation node", kind: "safety" },
      { id: "ref", label: "Refusal template", kind: "out" },
      { id: "hum", label: "Human analyst queue", kind: "out" },
    ],
    edges: [
      { from: "req", to: "gin" },
      { from: "gin", to: "e1" },
      { from: "e1", to: "esc" },
      { from: "esc", to: "ref" },
      { from: "esc", to: "hum" },
    ],
    steps: [
      { active: ["req"], note: "Override risk assessment / Ignore regulatory limits" },
      { active: ["gin"], note: "Pattern match + LLM paraphrase classifier catch bypass intent." },
      { active: ["e1"], note: "E1 fires — never begin constructing a partial answer." },
      { active: ["esc"], note: "Escalation terminal: build handoff envelope (trigger, evidence, reviewer)." },
      {
        active: ["ref", "hum"],
        note: "Refusal (no method disclosed) + mandatory human handoff. Escalation Recall = 1.0.",
      },
    ],
  },
  {
    id: "ingest",
    title: "Offline Ingestion (Sprint 4)",
    subtitle: "Corpus ? chunks ? embeddings; SQL seed ? finance_risk_db",
    budget: "batch",
    nodes: [
      { id: "pdf", label: "7 policy PDFs", kind: "store" },
      { id: "ext", label: "Extract + sections", kind: "agent" },
      { id: "chk", label: "Chunk (~800 tok)", kind: "agent" },
      { id: "emb", label: "Embed", kind: "agent" },
      { id: "vec", label: "policy_chunks", kind: "store" },
      { id: "smoke", label: "20-probe smoke", kind: "safety" },
      { id: "gen", label: "SQL generator", kind: "agent" },
      { id: "db", label: "finance_risk_db", kind: "store" },
      { id: "pre", label: "Golden preconditions", kind: "safety" },
    ],
    edges: [
      { from: "pdf", to: "ext" },
      { from: "ext", to: "chk" },
      { from: "chk", to: "emb" },
      { from: "emb", to: "vec" },
      { from: "vec", to: "smoke" },
      { from: "gen", to: "db" },
      { from: "db", to: "pre" },
    ],
    steps: [
      { active: ["pdf"], note: "Strategy, risk, regulatory, market, monitoring, Basel III, framework." },
      { active: ["ext"], note: "Per-page extract; keep page numbers; detect section headings." },
      { active: ["chk"], note: "~800 tokens / 120 overlap; never split a limits table." },
      { active: ["emb", "vec"], note: "Upsert embeddings + {doc_id, section, page} metadata." },
      { active: ["smoke"], note: "Validate retrieval with 20 known-answer probes." },
      { active: ["gen", "db"], note: "Seeded INSERT into 5 business tables." },
      { active: ["pre"], note: "Extend rows required by golden queries; assert data preconditions." },
    ],
  },
  {
    id: "guard",
    title: "Guardrail & Escalation Engine",
    subtitle: "Deterministic E1–E8 before any answer ships",
    budget: "hard gate",
    nodes: [
      { id: "q", label: "Analyst query", kind: "boundary" },
      { id: "pat", label: "Pattern match", kind: "safety" },
      { id: "llm", label: "Intent classifier", kind: "route" },
      { id: "path", label: "Agent path", kind: "agent" },
      { id: "ev", label: "Evidence bundle", kind: "store" },
      { id: "rules", label: "E2–E8 checks", kind: "safety" },
      { id: "ok", label: "No trigger", kind: "out" },
      { id: "esc", label: "Escalation terminal", kind: "safety" },
      { id: "syn", label: "Synthesis", kind: "agent" },
      { id: "ov", label: "Output validator", kind: "out" },
    ],
    edges: [
      { from: "q", to: "pat" },
      { from: "pat", to: "llm" },
      { from: "pat", to: "esc" },
      { from: "llm", to: "path" },
      { from: "llm", to: "esc" },
      { from: "path", to: "ev" },
      { from: "ev", to: "rules" },
      { from: "rules", to: "ok" },
      { from: "rules", to: "esc" },
      { from: "ok", to: "syn" },
      { from: "syn", to: "ov" },
      { from: "esc", to: "ov" },
    ],
    steps: [
      { active: ["q"], note: "Every query enters Safety before expensive retrieval." },
      { active: ["pat"], note: "Deterministic lexicon: override, ignore, bypass, waive, despite flag" },
      { active: ["llm"], note: "If clean of patterns, LLM checks paraphrased bypass." },
      { active: ["path", "ev"], note: "Clean ? router path; agents write typed evidence only." },
      {
        active: ["rules"],
        note: "E2 flag · E3 score>80 · E4 conflict · E5 weak evidence · E6 limit · E7 unapproved · E8 low conf.",
      },
      { active: ["esc", "ov"], note: "Any hard trigger ? terminal handoff; never partial fulfillment." },
      { active: ["ok", "syn", "ov"], note: "Clear ? evidence-only Synthesis ? citation/advice validator." },
    ],
  },
];

function kindColor(
  kind: FlowNode["kind"],
  theme: ReturnType<typeof useHostTheme>,
  active: boolean,
): { fill: string; stroke: string; text: string } {
  if (active) {
    return {
      fill: colorPalette.purple,
      stroke: colorPalette.purple,
      text: theme.text.onAccent,
    };
  }
  // Distinct categorical hues (not near-identical greys)
  switch (kind) {
    case "safety":
      return { fill: colorPalette.red, stroke: colorPalette.orange, text: theme.text.primary };
    case "agent":
      return { fill: colorPalette.cyan, stroke: colorPalette.cyan, text: theme.text.primary };
    case "store":
      return { fill: colorPalette.yellow, stroke: colorPalette.orange, text: theme.text.primary };
    case "route":
      return { fill: colorPalette.blue, stroke: colorPalette.blue, text: theme.text.primary };
    case "out":
      return { fill: colorPalette.green, stroke: colorPalette.green, text: theme.text.primary };
    default:
      return { fill: colorPalette.gray, stroke: theme.stroke.primary, text: theme.text.primary };
  }
}

function AnimatedFlowGraph({
  flow,
  stepIndex,
}: {
  flow: FlowDef;
  stepIndex: number;
}) {
  const theme = useHostTheme();
  const layout = useMemo(
    () =>
      computeDAGLayout({
        nodes: flow.nodes.map((n) => ({ id: n.id })),
        edges: flow.edges,
        direction: "horizontal",
        nodeWidth: 132,
        nodeHeight: 44,
        rankGap: 56,
        nodeGap: 28,
        padding: 20,
      }),
    [flow],
  );

  const activeIds = new Set(flow.steps[stepIndex]?.active ?? []);
  const nodeMeta = useMemo(() => {
    const m = new Map<string, FlowNode>();
    for (const n of flow.nodes) m.set(n.id, n);
    return m;
  }, [flow]);

  const pulse = (Date.now() / 400) % 1; // overwritten by CSS animation below

  return (
    <div style={{ overflowX: "auto", width: "100%" }}>
      <svg
        width={layout.width}
        height={layout.height}
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        style={{ display: "block", maxWidth: "100%" }}
      >
        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={theme.stroke.secondary} />
          </marker>
          <marker
            id="arrowActive"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={colorPalette.purple} />
          </marker>
        </defs>

        {layout.edges.map((e, i) => {
          const edgeActive = activeIds.has(e.from) && activeIds.has(e.to);
          const midX = (e.sourceX + e.targetX) / 2;
          const d = `M ${e.sourceX} ${e.sourceY} C ${midX} ${e.sourceY}, ${midX} ${e.targetY}, ${e.targetX} ${e.targetY}`;
          return (
            <path
              key={`${e.from}-${e.to}-${i}`}
              d={d}
              fill="none"
              stroke={edgeActive ? colorPalette.purple : theme.stroke.tertiary}
              strokeWidth={edgeActive ? 2.5 : 1.25}
              strokeDasharray={e.isBackEdge ? "4 3" : edgeActive ? "8 4" : undefined}
              markerEnd={edgeActive ? "url(#arrowActive)" : "url(#arrow)"}
              opacity={edgeActive ? 1 : 0.55}
            >
              {edgeActive ? (
                <animate
                  attributeName="stroke-dashoffset"
                  from="24"
                  to="0"
                  dur="0.9s"
                  repeatCount="indefinite"
                />
              ) : null}
            </path>
          );
        })}

        {layout.nodes.map((n) => {
          const meta = nodeMeta.get(n.id)!;
          const active = activeIds.has(n.id);
          const colors = kindColor(meta.kind, theme, active);
          return (
            <g key={n.id} transform={`translate(${n.x}, ${n.y})`}>
              {active ? (
                <rect
                  x={-3}
                  y={-3}
                  width={132 + 6}
                  height={44 + 6}
                  rx={10}
                  fill="none"
                  stroke={colorPalette.purple}
                  strokeWidth={1.5}
                  opacity={0.45}
                >
                  <animate
                    attributeName="opacity"
                    values="0.25;0.7;0.25"
                    dur="1.2s"
                    repeatCount="indefinite"
                  />
                </rect>
              ) : null}
              <rect
                width={132}
                height={44}
                rx={8}
                fill={colors.fill}
                stroke={colors.stroke}
                strokeWidth={active ? 2 : 1}
              />
              <text
                x={66}
                y={26}
                textAnchor="middle"
                fill={colors.text}
                fontSize={11}
                fontFamily="system-ui, sans-serif"
                fontWeight={active ? 600 : 500}
              >
                {meta.label.length > 18 ? meta.label.slice(0, 17) + "" : meta.label}
              </text>
            </g>
          );
        })}
      </svg>
      {/* silence unused */}
      <span style={{ display: "none" }}>{pulse}</span>
    </div>
  );
}

function stepLabels(flow: FlowDef, active: string[]): string[] {
  const map = new Map(flow.nodes.map((n) => [n.id, n.label]));
  return active.map((id) => map.get(id) ?? id);
}

function stepHeadline(flow: FlowDef, active: string[]): string {
  const labels = stepLabels(flow, active);
  if (labels.length === 1) return labels[0];
  if (labels.length === 2) return `${labels[0]} ? ${labels[1]}`;
  return `${labels[0]} ? … ? ${labels[labels.length - 1]} (${labels.length} nodes)`;
}

function StepRail({
  flow,
  stepIndex,
  onSelect,
}: {
  flow: FlowDef;
  stepIndex: number;
  onSelect: (i: number) => void;
}) {
  const theme = useHostTheme();
  return (
    <Stack gap={8}>
      {flow.steps.map((s, i) => {
        const on = i === stepIndex;
        const done = i < stepIndex;
        const labels = stepLabels(flow, s.active);
        return (
          <button
            key={i}
            type="button"
            onClick={() => onSelect(i)}
            style={{
              textAlign: "left",
              border: `1px solid ${on ? colorPalette.purple : theme.stroke.tertiary}`,
              background: on ? theme.fill.primary : theme.bg.elevated,
              color: theme.text.primary,
              borderRadius: 10,
              padding: "12px 14px",
              cursor: "pointer",
              borderLeftWidth: 3,
              borderLeftColor: on
                ? colorPalette.purple
                : done
                  ? colorPalette.green
                  : theme.stroke.tertiary,
            }}
          >
            <Stack gap={4}>
              <Row gap={10} align="center">
                <Pill size="sm" active={on}>{`Step ${i + 1} of ${flow.steps.length}`}</Pill>
                <Text size="small" weight="semibold">
                  {stepHeadline(flow, s.active)}
                </Text>
              </Row>
              <Text size="small" tone="secondary">
                Path: {labels.join(" ? ")}
              </Text>
              <Text size="small" weight={on ? "semibold" : "normal"}>
                {s.note}
              </Text>
            </Stack>
          </button>
        );
      })}
    </Stack>
  );
}

export default function AnimatedSystemFlows() {
  const theme = useHostTheme();
  const [flowId, setFlowId] = useState<FlowId>("arch");
  const [stepIndex, setStepIndex] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [ms, setMs] = useState(1400);

  const flow = FLOWS.find((f) => f.id === flowId)!;

  useEffect(() => {
    setStepIndex(0);
    setPlaying(true);
  }, [flowId]);

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => {
      setStepIndex((s) => (s + 1) % flow.steps.length);
    }, ms);
    return () => clearInterval(id);
  }, [playing, ms, flow.steps.length]);

  return (
    <Stack gap={20} style={{ padding: 20, maxWidth: 1100 }}>
      <Stack gap={6}>
        <H1>Animated architecture & system flows</H1>
        <Text tone="secondary">
          Start with System Context and Architecture Flow (C4), then the four-band system journey,
          LangGraph orchestration, and per-category paths (C1–C5). Source: planning/06 + 03.
        </Text>
      </Stack>

      <Row gap={12} wrap>
        <Stat label="Arch diagrams" value="4" />
        <Stat label="Category paths" value="5" />
        <Stat label="Hard safety SLOs" value="4" tone="warning" />
        <Stat label="Active" value={flow.budget} />
      </Row>

      <Card>
        <CardHeader trailing={playing ? "Playing" : "Paused"}>Flow selector</CardHeader>
        <CardBody>
          <Stack gap={12}>
            <Row gap={8} wrap>
              <Button
                variant={playing ? "secondary" : "primary"}
                onClick={() => setPlaying((p) => !p)}
              >
                {playing ? "Pause" : "Play"}
              </Button>
              <Button
                variant="secondary"
                onClick={() => setStepIndex((s) => (s - 1 + flow.steps.length) % flow.steps.length)}
              >
                Prev
              </Button>
              <Button
                variant="secondary"
                onClick={() => setStepIndex((s) => (s + 1) % flow.steps.length)}
              >
                Next
              </Button>
            </Row>
            <Row gap={16} wrap align="end">
              <Stack gap={4} style={{ minWidth: 280, flex: 1 }}>
                <Text size="small" weight="semibold">
                  Diagram
                </Text>
                <Select
                  value={flowId}
                  onChange={(v) => setFlowId(v as FlowId)}
                  options={FLOWS.map((f) => ({ value: f.id, label: f.title }))}
                />
              </Stack>
              <Stack gap={4} style={{ minWidth: 180 }}>
                <Text size="small" weight="semibold">
                  Animation speed
                </Text>
                <Select
                  value={String(ms)}
                  onChange={(v) => setMs(Number(v))}
                  options={[
                    { value: "900", label: "Fast (0.9s)" },
                    { value: "1400", label: "Normal (1.4s)" },
                    { value: "2200", label: "Slow (2.2s)" },
                  ]}
                />
              </Stack>
            </Row>
          </Stack>
        </CardBody>
      </Card>

      <Stack gap={8}>
        <Row gap={10} align="center" wrap>
          <H2>{flow.title}</H2>
          <Pill tone="info">{flow.budget}</Pill>
          <Pill tone="neutral">{`Step ${stepIndex + 1} / ${flow.steps.length}`}</Pill>
        </Row>
        <Text tone="secondary">{flow.subtitle}</Text>
      </Stack>

      <Callout
        tone="info"
        title={`Step ${stepIndex + 1} of ${flow.steps.length}: ${stepHeadline(flow, flow.steps[stepIndex].active)}`}
      >
        {flow.steps[stepIndex].note}
      </Callout>

      <Card>
        <CardHeader>Live path animation</CardHeader>
        <CardBody>
          <AnimatedFlowGraph flow={flow} stepIndex={stepIndex} />
          <Divider />
          <Row gap={16} wrap style={{ marginTop: 12 }}>
            <Row gap={6} align="center">
              <span style={{ width: 12, height: 12, borderRadius: 3, background: colorPalette.purple }} />
              <Text size="small">Active</Text>
            </Row>
            <Row gap={6} align="center">
              <span style={{ width: 12, height: 12, borderRadius: 3, background: colorPalette.gray }} />
              <Text size="small">Boundary</Text>
            </Row>
            <Row gap={6} align="center">
              <span style={{ width: 12, height: 12, borderRadius: 3, background: colorPalette.blue }} />
              <Text size="small">Route</Text>
            </Row>
            <Row gap={6} align="center">
              <span style={{ width: 12, height: 12, borderRadius: 3, background: colorPalette.cyan }} />
              <Text size="small">Agent</Text>
            </Row>
            <Row gap={6} align="center">
              <span style={{ width: 12, height: 12, borderRadius: 3, background: colorPalette.yellow }} />
              <Text size="small">Store</Text>
            </Row>
            <Row gap={6} align="center">
              <span style={{ width: 12, height: 12, borderRadius: 3, background: colorPalette.red }} />
              <Text size="small">Safety</Text>
            </Row>
            <Row gap={6} align="center">
              <span style={{ width: 12, height: 12, borderRadius: 3, background: colorPalette.green }} />
              <Text size="small">Output</Text>
            </Row>
          </Row>
        </CardBody>
      </Card>

      <Stack gap={8}>
        <H3>Step timeline</H3>
        <Text size="small" tone="secondary">
          Click a step to jump. Purple highlight = current; green left edge = completed.
        </Text>
        <StepRail flow={flow} stepIndex={stepIndex} onSelect={setStepIndex} />
      </Stack>

      <Callout tone="neutral" title="Source">
        planning/06_High_Level_Architecture.md §1–6 · planning/03_Initial_System_Blueprint.md §3
      </Callout>
    </Stack>
  );
}

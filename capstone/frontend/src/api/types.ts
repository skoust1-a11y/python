export type Role = "analyst" | "risk_manager" | "compliance" | "admin";
export type Outcome = "answered" | "refused" | "escalated" | "insufficient_evidence";

export type User = {
  user_id: string;
  email: string;
  role: Role;
  portfolio_ids: number[];
  full_name?: string | null;
  status: string;
  features: { current_factors: boolean };
};

export type DocRole = "strategy" | "matrix" | "policy";
export type DocOrigin = "system" | "user";

export type Citation =
  | {
      type: "doc";
      doc_id: string;
      doc_title: string;
      section: string;
      page: number;
      chunk_id: string;
      score: number;
      doc_category?: string | null;
      filename?: string | null;
      origin?: DocOrigin;
      role?: DocRole | null;
      excerpt?: string | null;
    }
  | {
      type: "sql";
      query_id: string;
      tables: string[];
      params: Record<string, unknown>;
      row_count: number;
      executed_at: string;
    }
  | {
      type: "quote";
      symbol: string;
      price: number;
      as_of: string;
      provider_id: string;
      stale?: boolean;
    }
  | {
      type: "news";
      headline: string;
      source: string;
      url: string;
      published_at: string;
      provider_id: string;
    };

export type PolicyUseCase =
  | "strategy"
  | "risk"
  | "regulatory"
  | "research"
  | "evaluation"
  | "framework"
  | "matrix"
  | "C1_RAG"
  | "C3_HYBRID"
  | "C4_HIGH_RISK"
  | "all";

export type PolicyDocument = {
  doc_id: string;
  doc_title: string;
  filename: string;
  category: string;
  role: DocRole;
  origin: DocOrigin;
  use_case?: PolicyUseCase | string;
  kind?: string;
  symbol?: string | null;
  chunk_count?: number;
  preview?: string;
  has_file?: boolean;
};

export type PolicyChunk = {
  chunk_id: string;
  section: string;
  page: number;
  chunk_text: string;
};

export type PolicyDocumentDetail = {
  document: PolicyDocument;
  chunks: PolicyChunk[];
  disclaimer: string;
};

export type QueryResponse = {
  trace_id: string;
  session_id: string;
  outcome: Outcome;
  answer: string;
  data_tables?: Array<{
    title: string;
    columns: string[];
    rows: string[][];
    total_rows: number;
  }>;
  citations: Citation[];
  routing: {
    category: string;
    category_label: string;
    path: string[];
    agents_used: string[];
    confidence: number;
    rationale?: string | null;
  };
  risk: {
    level?: string | null;
    rationale?: string | null;
    any_escalation_flag: boolean;
    breached_thresholds: Array<{
      name: string;
      policy_value: number;
      observed_value: number;
      unit: string;
    }>;
    flagged_assets: Array<{
      asset_name: string;
      risk_id: number;
      risk_score: number;
      escalation_flag: boolean;
    }>;
  };
  escalation: {
    required: boolean;
    triggers: string[];
    reason?: string | null;
    recommended_reviewer?: string | null;
    escalation_id?: string | null;
  };
  confidence: number;
  gaps: string[];
  disclaimer: string;
  latency_ms: number;
  token_usage?: { prompt?: number; completion?: number; total?: number };
  cost_usd?: number;
  model_info?: Record<string, string>;
  evidence_mode_used: "corpus" | "current";
  saved_note?: boolean;
  evidence_summary?: {
    doc_chunks: number;
    sql_queries: number;
    sql_rows: number;
    quotes?: number;
    news?: number;
  };
};

export type ChatSession = {
  session_id: string;
  title: string;
  created_at?: string | null;
};

export type ChatTurn = {
  turn_id: number;
  query: string;
  answer?: string | null;
  outcome: Outcome;
  category?: string | null;
  created_at?: string | null;
};

export type Holding = {
  holding_id: number;
  portfolio_id: number;
  asset_name: string;
  asset_type: string;
  sector: string;
  allocation_percentage: number;
  market_value: number;
  buy_price?: number | null;
  buy_date?: string | null;
  last_updated?: string;
};

export type PortfolioBook = {
  portfolio_id: number;
  portfolio_name: string;
  portfolio_manager: string;
  risk_category: string;
  total_value: number;
  benchmark_index: string;
  holdings: Holding[];
};

export type ScreenDefinition = {
  version: number;
  logic: "and" | "or";
  filters: Array<{ field: string; op: string; value?: unknown }>;
  sort: Array<{ field: string; dir: "asc" | "desc" }>;
  limit: number;
  period: { type: "FY" | "Q"; as_of: string };
};

export type ScreenRun = {
  trace_id?: string;
  row_count: number;
  columns: string[];
  rows: Record<string, unknown>[];
  definition?: ScreenDefinition;
  disclaimer: string;
};

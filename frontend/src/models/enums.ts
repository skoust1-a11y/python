export type AnalysisType =
  | "stock_analysis"
  | "portfolio_risk"
  | "portfolio_review"
  | "portfolio_rebalancing";

export type RiskTolerance = "conservative" | "moderate" | "aggressive";
export type InvestmentHorizon = "short" | "medium" | "long";
export type WorkflowStatus = "pending" | "running" | "completed" | "failed";
export type AgentRunStatus = "succeeded" | "failed";
export type ConflictSeverity = "info" | "warning" | "error";
export type CritiqueCategory =
  | "missing_evidence"
  | "unsupported_recommendation"
  | "agent_disagreement"
  | "missing_analysis"
  | "stale_or_unavailable_data"
  | "constraint_violation";
export type CritiqueSeverity = "info" | "warning" | "critical";
export type AsOfKind = "latest_reported" | "historical" | "current_market";

export type PortfolioFormat = "csv" | "xlsx";
export type PreviewStatus = "valid" | "valid_with_warnings" | "invalid";
export type IssueSeverity = "error" | "warning";
export type SymbolValidationStatus = "valid" | "invalid" | "missing";
export type PortfolioStatus = "imported";
export type StatementType = "income" | "balance_sheet" | "cash_flow";
export type ReportingPeriod = "annual" | "quarterly";

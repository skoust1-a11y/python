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

export interface ProfileOption<T> {
  value: T;
  label: string;
  detail: string;
  description: string;
}

export const RISK_TOLERANCE_OPTIONS: ProfileOption<RiskTolerance>[] = [
  {
    value: "conservative",
    label: "Conservative (< 10% Drawdown / Capital Preservation)",
    detail: "Loss tolerance < 10%",
    description: "Prioritizes capital protection, low volatility, and defensive holdings with minimal drawdown.",
  },
  {
    value: "moderate",
    label: "Moderate (10%–20% Drawdown / Balanced Growth)",
    detail: "Loss tolerance 10%–20%",
    description: "Balances growth with standard benchmark-level volatility and moderate drawdown tolerance.",
  },
  {
    value: "aggressive",
    label: "Aggressive (> 20% Drawdown / Maximum Growth)",
    detail: "Loss tolerance > 20%",
    description: "Maximizes capital appreciation; accepts high beta, high volatility, and significant cyclical drawdowns.",
  },
];

export const HORIZON_OPTIONS: ProfileOption<InvestmentHorizon>[] = [
  {
    value: "short",
    label: "Short term (< 1 year / 0–12 months)",
    detail: "0 to 12 months",
    description: "Near-term liquidity and tactical momentum; emphasizes capital preservation over multi-year compounding.",
  },
  {
    value: "medium",
    label: "Medium term (1 to 5 years)",
    detail: "1 to 5 years",
    description: "Multi-year holding horizon; balances cyclical economic swings with fundamental compounding.",
  },
  {
    value: "long",
    label: "Long term (5+ years)",
    detail: "5+ years",
    description: "Long-range equity compounding across multiple market cycles; rides out temporary market downturns.",
  },
];


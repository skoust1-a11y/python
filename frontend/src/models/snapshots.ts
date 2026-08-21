import type { DataSourceMetadata } from "./common";
import type { AsOfKind, CritiqueCategory, CritiqueSeverity } from "./enums";

export interface SelectedStock {
  symbol: string;
  name: string | null;
}

export interface MarketDataSnapshot {
  symbol: string;
  current_price: number | null;
  currency: string | null;
  exchange: string | null;
  change_percent: number | null;
  volume: number | null;
  trend: string | null;
  volatility: number | null;
  momentum: number | null;
  as_of: string | null;
  unavailable: string[];
  source: DataSourceMetadata | null;
}

export interface FundamentalDataSnapshot {
  symbol: string;
  company_name: string | null;
  sector: string | null;
  industry: string | null;
  financial_health: string | null;
  profitability: string | null;
  revenue: number | null;
  earnings: number | null;
  pe_ratio: number | null;
  reporting_period: string | null;
  as_of_kind: AsOfKind | null;
  as_of: string | null;
  unavailable: string[];
  source: DataSourceMetadata | null;
}

export interface NewsSnapshot {
  headline: string;
  timestamp: string;
  source: DataSourceMetadata;
  publisher: string | null;
  symbol: string | null;
  url: string | null;
}

export interface RiskAnalysisSnapshot {
  overall_risk_assessment: string | null;
  concentration: string | null;
  diversification: string | null;
  weight_basis: string | null;
  largest_symbol: string | null;
  largest_weight: number | null;
  hhi: number | null;
  portfolio_volatility: number | null;
  max_drawdown: number | null;
  beta?: number | null;
  benchmark_correlation?: number | null;
  major_risks: string[];
  unavailable: string[];
  portfolio_id: string | null;
}

export interface OptimizationResultSnapshot {
  objective: string | null;
  current_allocation: Record<string, number>;
  proposed_allocation: Record<string, number>;
  feasible: boolean | null;
  solver_status: string | null;
  warnings: string[];
  limitations: string[];
  trade_execution: "not_implemented";
}

export interface ConflictRecord {
  description: string;
  agents: string[];
  severity: "info" | "warning" | "error";
}

export interface CritiqueRecord {
  author: string;
  message: string;
  target: string | null;
  category: CritiqueCategory | null;
  severity: CritiqueSeverity;
  resolved: boolean;
}

export interface FinalRecommendation {
  summary: string;
  recommendation: string;
  findings: string[];
  risks: string[];
  assumptions: string[];
  limitations: string[];
  confidence: number | null;
  trade_execution: "not_implemented";
}

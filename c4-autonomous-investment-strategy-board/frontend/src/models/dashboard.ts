import type { Evidence } from "./common";

export type MarketSession = "open" | "closed" | "pre_market" | "after_hours" | "unknown";
export type WeightBasis = "market_value" | "uploaded_weight" | "cost_value" | "insufficient_data";
export type ConcentrationLabel = "low" | "moderate" | "high" | "insufficient_data";
export type DiversificationLabel = "diversified" | "moderate" | "concentrated" | "insufficient_data";

export interface IndexOverview {
  symbol: string;
  name: string | null;
  value: number | null;
  change: number | null;
  change_percent: number | null;
  timestamp: string | null;
  currency: string | null;
  exchange: string | null;
}

export interface MarketOverview {
  nifty50: IndexOverview | null;
  indices: IndexOverview[];
  session: MarketSession;
  timezone: string | null;
  trading_hours: string | null;
  as_of: string | null;
  provider: string | null;
  unavailable: string[];
  evidence: Evidence[];
}

export interface AllocationSlice {
  symbol: string;
  name: string | null;
  weight: number | null;
  market_value: number | null;
}

export interface PortfolioRiskOverview {
  concentration: ConcentrationLabel;
  diversification: DiversificationLabel;
  largest_symbol: string | null;
  largest_weight: number | null;
  hhi: number | null;
  effective_n: number | null;
  top3_share: number | null;
  oversized_symbols: string[];
  weight_basis: WeightBasis;
}

export interface PortfolioOverview {
  id: string;
  name: string | null;
  holding_count: number;
  market_value: number | null;
  day_change: number | null;
  day_change_percent: number | null;
  cost_value: number | null;
  currency: string | null;
  mixed_currency: boolean;
  allocation: AllocationSlice[];
  risk: PortfolioRiskOverview;
  imported_at: string;
  quoted_holding_count: number;
  unavailable: string[];
  evidence: Evidence[];
}

export interface DashboardOverview {
  market: MarketOverview;
  portfolio: PortfolioOverview | null;
}

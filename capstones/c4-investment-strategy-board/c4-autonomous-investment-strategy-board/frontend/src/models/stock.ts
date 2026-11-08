import type { Evidence } from "./common";
import type { CompanyProfile, FinancialMetrics, ValuationMetrics } from "./fundamentals";
import type {
  InstrumentMatch,
  MarketInfo,
  MarketQuote,
  OhlcSeries,
  VolumeSnapshot,
} from "./market";
import type { FundamentalDataSnapshot, MarketDataSnapshot, SelectedStock } from "./snapshots";

export interface StockSearchResponse {
  query: string;
  matches: InstrumentMatch[];
}

export interface StockSelectionRequest {
  symbol: string;
}

export interface SuggestedQuestion {
  id: string;
  question: string;
  topic: string;
}

export interface SuggestedQuestionList {
  symbol: string;
  questions: SuggestedQuestion[];
}

export interface StockOverview {
  symbol: string;
  name: string | null;
  exchange: string | null;
  currency: string | null;
  asset_class: string | null;
  quote: MarketQuote | null;
  volume: VolumeSnapshot | null;
  market_info: MarketInfo | null;
  profile: CompanyProfile | null;
  selected: SelectedStock;
  unavailable: string[];
  evidence: Evidence[];
}

export interface StockMarketData {
  symbol: string;
  quote: MarketQuote | null;
  volume: VolumeSnapshot | null;
  market_info: MarketInfo | null;
  history: OhlcSeries | null;
  snapshot: MarketDataSnapshot | null;
  unavailable: string[];
  evidence: Evidence[];
}

export interface StockFundamentalData {
  symbol: string;
  profile: CompanyProfile | null;
  metrics: FinancialMetrics | null;
  valuation: ValuationMetrics | null;
  snapshot: FundamentalDataSnapshot | null;
  unavailable: string[];
  evidence: Evidence[];
}

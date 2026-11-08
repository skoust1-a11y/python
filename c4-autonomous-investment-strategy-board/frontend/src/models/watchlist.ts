import type { Evidence } from "./common";
import type { MarketQuote, VolumeSnapshot } from "./market";
import type { SelectedStock } from "./snapshots";
import type { StockOverview } from "./stock";

export interface WatchlistAddRequest {
  symbol: string;
}

export interface WatchlistItem {
  symbol: string;
  name: string | null;
  exchange: string | null;
  currency: string | null;
  added_at: string;
  quote: MarketQuote | null;
  volume: VolumeSnapshot | null;
  unavailable: string[];
  evidence: Evidence[];
  analyzer_path: string;
}

export interface WatchlistRemoval {
  symbol: string;
  removed: boolean;
}

export interface WatchlistOpenResponse {
  symbol: string;
  selected: SelectedStock;
  overview: StockOverview;
  analyzer_path: string;
}

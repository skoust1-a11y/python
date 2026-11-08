import type { DataSourceMetadata, JsonObject } from "./common";

export interface InstrumentMatch {
  symbol: string;
  source: DataSourceMetadata;
  name: string | null;
  exchange: string | null;
  currency: string | null;
  asset_class: string | null;
  extra: JsonObject;
}

export interface MarketQuote {
  symbol: string;
  value: number;
  timestamp: string;
  currency: string | null;
  exchange: string | null;
  bid: number | null;
  ask: number | null;
  change: number | null;
  change_percent: number | null;
  volume: number | null;
  source: DataSourceMetadata;
  extra: JsonObject;
}

export interface HistoricalPrice {
  symbol: string;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  period: string;
  volume: number | null;
  currency: string | null;
  exchange: string | null;
  source: DataSourceMetadata;
  extra: JsonObject;
  value: number;
}

export interface OhlcSeries {
  symbol: string;
  period: string;
  source: DataSourceMetadata;
  start: string | null;
  end: string | null;
  prices: HistoricalPrice[];
  extra: JsonObject;
}

export interface VolumeSnapshot {
  symbol: string;
  value: number;
  timestamp: string;
  average_volume: number | null;
  currency: string | null;
  exchange: string | null;
  source: DataSourceMetadata;
  extra: JsonObject;
}

export interface MarketInfo {
  symbol: string;
  source: DataSourceMetadata;
  name: string | null;
  exchange: string | null;
  currency: string | null;
  asset_class: string | null;
  timezone: string | null;
  trading_hours: string | null;
  session: string | null;
  extra: JsonObject;
}

export interface MarketIndex {
  symbol: string;
  value: number;
  timestamp: string;
  name: string | null;
  currency: string | null;
  exchange: string | null;
  change: number | null;
  change_percent: number | null;
  constituents: string[] | null;
  source: DataSourceMetadata;
  extra: JsonObject;
}

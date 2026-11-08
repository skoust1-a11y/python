export type JsonObject = Record<string, unknown>;

export interface DataSourceMetadata {
  provider: string;
  source: string;
  timestamp: string;
  url: string | null;
  raw_reference: string | null;
}

export interface Evidence {
  source: DataSourceMetadata;
  symbol: string | null;
  period: string | null;
  field: string | null;
  value: number | string | null;
  excerpt: string | null;
}

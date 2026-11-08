import type { DataSourceMetadata, JsonObject } from "./common";
import type { ReportingPeriod, StatementType } from "./enums";

export interface CompanyProfile {
  symbol: string;
  source: DataSourceMetadata;
  name: string | null;
  sector: string | null;
  industry: string | null;
  description: string | null;
  country: string | null;
  currency: string | null;
  exchange: string | null;
  website: string | null;
  employees: number | null;
  timestamp: string | null;
  extra: JsonObject;
}

export interface FinancialStatement {
  symbol: string;
  statement_type: StatementType;
  period: ReportingPeriod;
  source: DataSourceMetadata;
  currency: string | null;
  exchange: string | null;
  period_end: string | null;
  fiscal_period: string | null;
  timestamp: string | null;
  line_items: Record<string, number | string | null>;
  extra: JsonObject;
}

export interface FinancialMetrics {
  symbol: string;
  source: DataSourceMetadata;
  period: string | null;
  timestamp: string | null;
  currency: string | null;
  exchange: string | null;
  revenue: number | null;
  net_income: number | null;
  eps: number | null;
  ebitda: number | null;
  operating_margin: number | null;
  profit_margin: number | null;
  roe: number | null;
  roa: number | null;
  debt_to_equity: number | null;
  current_ratio: number | null;
  pe_ratio: number | null;
  forward_pe: number | null;
  pb_ratio: number | null;
  ps_ratio: number | null;
  peg_ratio: number | null;
  ev_to_ebitda: number | null;
  market_cap: number | null;
  enterprise_value: number | null;
  dividend_yield: number | null;
  extra: JsonObject;
}

export interface ValuationMetrics {
  symbol: string;
  source: DataSourceMetadata;
  timestamp: string | null;
  currency: string | null;
  exchange: string | null;
  pe_ratio: number | null;
  forward_pe: number | null;
  pb_ratio: number | null;
  ps_ratio: number | null;
  peg_ratio: number | null;
  ev_to_ebitda: number | null;
  market_cap: number | null;
  enterprise_value: number | null;
  dividend_yield: number | null;
  extra: JsonObject;
}

import type {
  IssueSeverity,
  PortfolioFormat,
  PortfolioStatus,
  PreviewStatus,
  SymbolValidationStatus,
} from "./enums";

export interface ValidationIssue {
  severity: IssueSeverity;
  code: string;
  message: string;
  row: number | null;
  column: string | null;
  value: string | null;
}

export interface SymbolValidation {
  input: string | null;
  normalized: string | null;
  status: SymbolValidationStatus;
  reason: string | null;
}

export interface Holding {
  symbol: string;
  quantity: number;
  average_cost: number | null;
  currency: string | null;
  name: string | null;
  weight: number | null;
  symbol_validation: SymbolValidation;
  cost_value: number | null;
}

export interface PreviewHolding {
  row: number;
  symbol: string | null;
  quantity: number | null;
  average_cost: number | null;
  currency: string | null;
  name: string | null;
  weight: number | null;
  symbol_validation: SymbolValidation;
  valid: boolean;
  cost_value: number | null;
}

export interface Portfolio {
  id: string;
  status: PortfolioStatus;
  name: string | null;
  holdings: Holding[];
  base_currency: string | null;
  source_filename: string;
  source_format: PortfolioFormat;
  imported_at: string;
  upload_id: string | null;
  holding_count: number;
}

export interface PortfolioPreview {
  upload_id: string;
  status: PreviewStatus;
  can_confirm: boolean;
  filename: string;
  format: PortfolioFormat | null;
  holdings: PreviewHolding[];
  issues: ValidationIssue[];
  created_at: string;
  expires_at: string;
  imported_portfolio_id: string | null;
  holding_count: number;
  error_count: number;
  warning_count: number;
}

export interface PortfolioSummary {
  id: string;
  status: PortfolioStatus;
  name: string | null;
  holding_count: number;
  base_currency: string | null;
  source_filename: string;
  source_format: PortfolioFormat;
  imported_at: string;
}

export interface PortfolioHoldings {
  portfolio_id: string;
  holdings: Holding[];
  holding_count: number;
}

export interface ConfirmPortfolioRequest {
  name?: string | null;
}

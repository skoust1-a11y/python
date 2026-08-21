import type { Evidence } from "./common";
import type {
  AgentRunStatus,
  AnalysisType,
  InvestmentHorizon,
  RiskTolerance,
  WorkflowStatus,
} from "./enums";
import type {
  ConflictRecord,
  CritiqueRecord,
  FinalRecommendation,
  FundamentalDataSnapshot,
  MarketDataSnapshot,
  NewsSnapshot,
  OptimizationResultSnapshot,
  RiskAnalysisSnapshot,
} from "./snapshots";

export interface PortfolioAnalysisRequest {
  question: string;
  analysis_type?: AnalysisType | null;
  risk_tolerance?: RiskTolerance | null;
  horizon?: InvestmentHorizon | null;
  objective?: string | null;
  benchmark?: string | null;
  index_symbol?: string | null;
}

export interface StockAnalysisRequest {
  question: string;
  analysis_type?: AnalysisType | null;
  risk_tolerance?: RiskTolerance | null;
  horizon?: InvestmentHorizon | null;
  objective?: string | null;
  benchmark?: string | null;
  index_symbol?: string | null;
}

export interface SpecialistResult {
  agent: string;
  role: string;
  status: AgentRunStatus;
  summary: string;
  findings: string[];
  confidence: number | null;
  error_message: string | null;
}

export interface AnalysisExecution {
  status: WorkflowStatus;
  requested_agents: string[];
  invoked_agents: string[];
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  errors: string[];
}

export interface PortfolioAnalysisSummary {
  id: string;
  portfolio_id: string;
  question: string;
  analysis_type: AnalysisType | null;
  status: WorkflowStatus;
  created_at: string;
}

export interface PortfolioAnalysisResult {
  id: string;
  portfolio_id: string;
  question: string;
  analysis_type: AnalysisType | null;
  status: WorkflowStatus;
  recommendation: FinalRecommendation | null;
  specialist_results: SpecialistResult[];
  risk_analysis: RiskAnalysisSnapshot | null;
  optimization: OptimizationResultSnapshot | null;
  market_data: MarketDataSnapshot[];
  fundamental_data: FundamentalDataSnapshot[];
  news: NewsSnapshot[];
  evidence: Evidence[];
  conflicts: ConflictRecord[];
  critiques: CritiqueRecord[];
  execution: AnalysisExecution;
  created_at: string;
}

export interface StockAnalysisSummary {
  id: string;
  symbol: string;
  question: string;
  analysis_type: AnalysisType | null;
  status: WorkflowStatus;
  created_at: string;
}

export interface StockAnalysisResult {
  id: string;
  symbol: string;
  question: string;
  analysis_type: AnalysisType | null;
  status: WorkflowStatus;
  recommendation: FinalRecommendation | null;
  specialist_results: SpecialistResult[];
  risk_analysis: RiskAnalysisSnapshot | null;
  optimization: OptimizationResultSnapshot | null;
  market_data: MarketDataSnapshot[];
  fundamental_data: FundamentalDataSnapshot[];
  news: NewsSnapshot[];
  evidence: Evidence[];
  conflicts: ConflictRecord[];
  critiques: CritiqueRecord[];
  execution: AnalysisExecution;
  created_at: string;
}

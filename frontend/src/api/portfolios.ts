import { getJson, postForm, postJson } from "./client";
import type {
  ConfirmPortfolioRequest,
  Portfolio,
  PortfolioAnalysisRequest,
  PortfolioAnalysisResult,
  PortfolioAnalysisSummary,
  PortfolioHoldings,
  PortfolioPreview,
  PortfolioSummary,
} from "@/models";

export function uploadPortfolio(file: File): Promise<PortfolioPreview> {
  const form = new FormData();
  form.append("file", file);
  return postForm<PortfolioPreview>("/portfolios/uploads", form);
}

export function getPortfolioUpload(uploadId: string): Promise<PortfolioPreview> {
  return getJson<PortfolioPreview>(`/portfolios/uploads/${uploadId}`);
}

export function confirmPortfolioUpload(
  uploadId: string,
  payload?: ConfirmPortfolioRequest,
): Promise<Portfolio> {
  return postJson<Portfolio>(`/portfolios/uploads/${uploadId}/confirm`, payload ?? {});
}

export function listPortfolios(): Promise<PortfolioSummary[]> {
  return getJson<PortfolioSummary[]>("/portfolios");
}

export function getPortfolio(portfolioId: string): Promise<Portfolio> {
  return getJson<Portfolio>(`/portfolios/${portfolioId}`);
}

export function getPortfolioSummary(portfolioId: string): Promise<PortfolioSummary> {
  return getJson<PortfolioSummary>(`/portfolios/${portfolioId}/summary`);
}

export function getPortfolioHoldings(portfolioId: string): Promise<PortfolioHoldings> {
  return getJson<PortfolioHoldings>(`/portfolios/${portfolioId}/holdings`);
}

export function submitPortfolioAnalysis(
  portfolioId: string,
  payload: PortfolioAnalysisRequest,
): Promise<PortfolioAnalysisResult> {
  return postJson<PortfolioAnalysisResult>(`/portfolios/${portfolioId}/analysis`, payload);
}

export function listPortfolioAnalyses(
  portfolioId: string,
): Promise<PortfolioAnalysisSummary[]> {
  return getJson<PortfolioAnalysisSummary[]>(`/portfolios/${portfolioId}/analysis`);
}

export function getPortfolioAnalysis(
  portfolioId: string,
  analysisId: string,
): Promise<PortfolioAnalysisResult> {
  return getJson<PortfolioAnalysisResult>(
    `/portfolios/${portfolioId}/analysis/${analysisId}`,
  );
}

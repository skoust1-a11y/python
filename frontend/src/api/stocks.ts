import { getJson, postJson } from "./client";
import type {
  StockAnalysisRequest,
  StockAnalysisResult,
  StockAnalysisSummary,
  StockFundamentalData,
  StockMarketData,
  StockOverview,
  StockSearchResponse,
  SuggestedQuestionList,
} from "@/models";

export function searchStocks(query: string, limit?: number): Promise<StockSearchResponse> {
  return getJson<StockSearchResponse>("/stocks/search", { q: query, limit });
}

export function selectStock(symbol: string): Promise<StockOverview> {
  return postJson<StockOverview>("/stocks/select", { symbol });
}

export function getStock(symbol: string): Promise<StockOverview> {
  return getJson<StockOverview>(`/stocks/${encodeURIComponent(symbol)}`);
}

export function getStockMarket(
  symbol: string,
  interval?: string,
): Promise<StockMarketData> {
  return getJson<StockMarketData>(`/stocks/${encodeURIComponent(symbol)}/market`, {
    interval,
  });
}

export function getStockFundamentals(symbol: string): Promise<StockFundamentalData> {
  return getJson<StockFundamentalData>(
    `/stocks/${encodeURIComponent(symbol)}/fundamentals`,
  );
}

export function getSuggestedQuestions(symbol: string): Promise<SuggestedQuestionList> {
  return getJson<SuggestedQuestionList>(
    `/stocks/${encodeURIComponent(symbol)}/questions`,
  );
}

export function submitStockAnalysis(
  symbol: string,
  payload: StockAnalysisRequest,
): Promise<StockAnalysisResult> {
  return postJson<StockAnalysisResult>(
    `/stocks/${encodeURIComponent(symbol)}/analysis`,
    payload,
  );
}

export function listStockAnalyses(symbol: string): Promise<StockAnalysisSummary[]> {
  return getJson<StockAnalysisSummary[]>(
    `/stocks/${encodeURIComponent(symbol)}/analysis`,
  );
}

export function getStockAnalysis(
  symbol: string,
  analysisId: string,
): Promise<StockAnalysisResult> {
  return getJson<StockAnalysisResult>(
    `/stocks/${encodeURIComponent(symbol)}/analysis/${analysisId}`,
  );
}

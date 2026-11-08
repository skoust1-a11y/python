import type { QueryResponse } from "@/api/types";
import { countRelevantClauses, countSourceDocuments } from "@/lib/sourceStats";

export interface ResponseMetrics {
  confidence: number;
  faithfulness: number;
  relevance: number;
  latencyMs: number;
  documentCount: number;
  clauseCount: number;
}

/**
 * Derives display metrics from the query response payload.
 * Uses evidence-based scores from the backend when available; falls back to
 * retrieval-derived estimates for older API responses.
 */
export function computeResponseMetrics(
  response: QueryResponse,
  latencyMs?: number,
): ResponseMetrics {
  const scores = response.sources.map((s) => s.score).filter((s) => s > 0);
  const avgScore =
    scores.length > 0 ? scores.reduce((sum, s) => sum + s, 0) / scores.length : 0;
  const maxScore = scores.length > 0 ? Math.max(...scores) : 0;

  const hasBackendMetrics =
    response.faithfulness > 0 ||
    response.relevance > 0 ||
    response.analysis_evaluation != null;

  const faithfulness = hasBackendMetrics
    ? response.faithfulness
    : scores.length > 0
      ? Math.min(response.confidence, avgScore * 0.85 + response.confidence * 0.15)
      : response.confidence * 0.45;

  const relevance = hasBackendMetrics
    ? response.relevance
    : maxScore > 0
      ? maxScore * 0.7 + avgScore * 0.3
      : response.related_documents.length > 0
        ? Math.max(...response.related_documents.map((d) => d.relevance))
        : response.confidence * 0.55;

  return {
    confidence: response.confidence,
    faithfulness,
    relevance,
    latencyMs: latencyMs ?? response.latency_ms,
    documentCount: countSourceDocuments(response.sources),
    clauseCount: countRelevantClauses(response.sources),
  };
}

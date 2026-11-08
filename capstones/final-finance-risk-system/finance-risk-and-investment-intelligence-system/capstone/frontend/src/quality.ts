import type { QueryResponse } from "./api/types";

export type QualityMeter = { label: string; hint: string; value: number };

export function qualityMeters(res: QueryResponse): QualityMeter[] {
  const s = res.evidence_summary;
  const evidence = (s?.doc_chunks || 0) + (s?.sql_queries || 0) + (s?.quotes || 0) + (s?.news || 0) || res.citations.length;
  const docScores = res.citations.flatMap((c) => (c.type === "doc" ? [c.score] : []));
  const meters = [
    { label: "Confidence", hint: "answer_confidence", value: res.confidence },
    { label: "Routing", hint: "category_confidence", value: res.routing.confidence },
    { label: "Evidence", hint: "citation_coverage", value: Math.min(1, evidence / 4) },
    { label: "Completeness", hint: "gap_ratio", value: res.gaps.length ? Math.max(0, 1 - res.gaps.length / 3) : 1 },
  ];
  if (docScores.length) {
    meters.push({ label: "Retrieval", hint: "top_doc_match (hybrid search)", value: Math.max(...docScores) });
  }
  return meters;
}

export function usageLine(res: QueryResponse): string {
  const tokens = (res.token_usage?.prompt || 0) + (res.token_usage?.completion || 0);
  const model = res.model_info?.synthesis || "deterministic";
  if (!tokens || model.startsWith("deterministic")) return "No LLM call (answer built from evidence)";
  return `${model} · ~${tokens} tokens (est.) · ~$${(res.cost_usd || 0).toFixed(4)}`;
}

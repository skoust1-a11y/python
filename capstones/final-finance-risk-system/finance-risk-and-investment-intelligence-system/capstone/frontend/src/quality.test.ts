import { describe, expect, it } from "vitest";
import type { QueryResponse } from "./api/types";
import { qualityMeters, usageLine } from "./quality";

const base = {
  confidence: 0.9,
  routing: { confidence: 0.8 },
  gaps: [],
  citations: [],
} as unknown as QueryResponse;

describe("qualityMeters", () => {
  it("adds a retrieval meter from the best doc citation", () => {
    const res = {
      ...base,
      citations: [
        { type: "doc", score: 0.4 },
        { type: "doc", score: 0.7 },
        { type: "sql", row_count: 3 },
      ],
      evidence_summary: { doc_chunks: 2, sql_queries: 1, sql_rows: 3 },
    } as unknown as QueryResponse;
    const byLabel = Object.fromEntries(qualityMeters(res).map((m) => [m.label, m.value]));
    expect(byLabel).toEqual({ Confidence: 0.9, Routing: 0.8, Evidence: 0.75, Completeness: 1, Retrieval: 0.7 });
  });

  it("skips retrieval without doc citations and penalises gaps", () => {
    const meters = qualityMeters({ ...base, gaps: ["a", "b", "c", "d"] });
    expect(meters.map((m) => m.label)).not.toContain("Retrieval");
    expect(meters.find((m) => m.label === "Completeness")?.value).toBe(0);
  });
});

describe("usageLine", () => {
  it("shows tokens and cost only when the LLM ran", () => {
    const used = { ...base, token_usage: { prompt: 100, completion: 20 }, cost_usd: 0.0021 };
    expect(usageLine({ ...used, model_info: { synthesis: "gemini-3.8-flash" } })).toBe("gemini-3.8-flash · ~120 tokens (est.) · ~$0.0021");
    expect(usageLine({ ...used, model_info: { synthesis: "deterministic_fallback" } })).toBe("No LLM call (answer built from evidence)");
    expect(usageLine(base)).toBe("No LLM call (answer built from evidence)");
  });
});

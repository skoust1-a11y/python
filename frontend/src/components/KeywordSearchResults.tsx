import type { DirectEvidenceItem } from "@/api/types";
import { DirectEvidenceResults } from "@/components/evidence/DirectEvidenceResults";

interface KeywordSearchResultsProps {
  results: DirectEvidenceItem[];
  totalCandidates: number;
  latencyMs: number;
  bm25HitCount?: number;
  semanticHitCount?: number;
}

/** @deprecated Use DirectEvidenceResults directly. */
export function KeywordSearchResults(props: KeywordSearchResultsProps) {
  return <DirectEvidenceResults {...props} />;
}

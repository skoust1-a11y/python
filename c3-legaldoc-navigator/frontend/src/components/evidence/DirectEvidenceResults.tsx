import type { DirectEvidenceItem } from "@/api/types";
import { DirectEvidenceCard } from "@/components/evidence/DirectEvidenceCard";

interface DirectEvidenceResultsProps {
  results: DirectEvidenceItem[];
  totalCandidates: number;
  latencyMs: number;
  bm25HitCount?: number;
  semanticHitCount?: number;
}

export function DirectEvidenceResults({
  results,
  totalCandidates,
  latencyMs,
  bm25HitCount,
  semanticHitCount,
}: DirectEvidenceResultsProps) {
  if (results.length === 0) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400">
        No matching excerpts found in {totalCandidates} indexed chunk
        {totalCandidates === 1 ? "" : "s"}.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500 dark:text-slate-400">
        {results.length} match{results.length === 1 ? "" : "es"} from {totalCandidates}{" "}
        indexed chunk
        {totalCandidates === 1 ? "" : "s"}
        {bm25HitCount != null && semanticHitCount != null && (
          <>
            {" "}
            · {bm25HitCount} keyword + {semanticHitCount} semantic candidates ranked
          </>
        )}
        {" · "}
        {latencyMs.toFixed(0)} ms
      </p>
      <ul className="list-none space-y-4">
        {results.map((item, index) => (
          <DirectEvidenceCard
            key={item.metadata.chunk_id}
            item={item}
            index={index}
          />
        ))}
      </ul>
    </div>
  );
}

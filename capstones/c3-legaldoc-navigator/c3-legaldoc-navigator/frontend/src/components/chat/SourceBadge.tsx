import { FileText } from "lucide-react";
import { countRelevantClauses, countSourceDocuments } from "@/lib/sourceStats";
import type { SourceCitation } from "@/api/types";

interface SourceBadgeProps {
  sources: SourceCitation[];
  active?: boolean;
  onClick?: () => void;
}

export function SourceBadge({ sources, active = false, onClick }: SourceBadgeProps) {
  const docCount = countSourceDocuments(sources);
  const clauseCount = countRelevantClauses(sources);

  if (sources.length === 0) return null;

  const label =
    clauseCount > 0
      ? `${docCount} doc${docCount !== 1 ? "s" : ""} · ${clauseCount} clause${clauseCount !== 1 ? "s" : ""}`
      : `${sources.length} source${sources.length !== 1 ? "s" : ""}`;

  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-all duration-200 focus-ring ${
        active
          ? "bg-brand-100 text-brand-800 ring-2 ring-brand-500/40 dark:bg-brand-900/50 dark:text-brand-200 dark:ring-brand-400/30"
          : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
      }`}
      title="View citations"
    >
      <FileText className="h-3.5 w-3.5" />
      {label}
    </button>
  );
}

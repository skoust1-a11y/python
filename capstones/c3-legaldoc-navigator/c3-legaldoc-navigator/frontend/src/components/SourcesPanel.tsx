import { useState } from "react";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import type { SourceCitation } from "@/api/types";
import { countRelevantClauses, countSourceDocuments } from "@/lib/sourceStats";
import { SourcesList } from "@/components/SourcesList";

interface SourcesPanelProps {
  sources: SourceCitation[];
  defaultExpanded?: boolean;
}

export function SourcesPanel({ sources, defaultExpanded = true }: SourcesPanelProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const docCount = countSourceDocuments(sources);
  const clauseCount = countRelevantClauses(sources);

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200/80 bg-slate-50/50 dark:border-slate-700/80 dark:bg-slate-900/40">
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-slate-100/80 dark:hover:bg-slate-800/50"
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-100 dark:bg-brand-900/40">
            <FileText className="h-4 w-4 text-brand-600 dark:text-brand-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">Sources</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {docCount} {docCount === 1 ? "Document" : "Documents"}
              {clauseCount > 0 && (
                <>
                  {" "}
                  · {clauseCount} Relevant {clauseCount === 1 ? "Clause" : "Clauses"}
                </>
              )}
            </p>
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 shrink-0 text-slate-400" />
        ) : (
          <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-slate-200/80 px-4 py-3 dark:border-slate-700/80">
          <SourcesList sources={sources} />
        </div>
      )}
    </div>
  );
}

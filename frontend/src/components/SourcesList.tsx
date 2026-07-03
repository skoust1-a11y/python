import { Link } from "react-router-dom";
import { ExternalLink, FileText, Hash } from "lucide-react";
import type { CitationLocation, SourceCitation } from "@/api/types";
import { formatPercent } from "@/lib/utils";

interface SourcesListProps {
  sources: SourceCitation[];
  compact?: boolean;
  variant?: "default" | "panel";
}

function formatLocation(location: CitationLocation): string {
  const parts: string[] = [];
  if (location.clause_number) {
    parts.push(`Clause ${location.clause_number}`);
  }
  if (location.clause_title) {
    parts.push(location.clause_title);
  }
  if (location.page_number != null) {
    parts.push(`Page ${location.page_number}`);
  }
  return parts.join(" · ");
}

export function SourcesList({ sources, compact = false }: SourcesListProps) {
  if (sources.length === 0) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400">No sources retrieved.</p>
    );
  }

  return (
    <ul className={compact ? "list-none space-y-2" : "list-none space-y-3"}>
      {sources.map((source, sourceIndex) => {
        const key = source.document_id ?? `${source.entity_type}-${source.entity_id}`;
        return (
          <li
            key={key}
            className={`animate-slide-up rounded-xl border border-slate-200/80 bg-slate-50/80 transition-colors hover:border-brand-200/60 hover:bg-brand-50/30 dark:border-slate-700/80 dark:bg-slate-800/40 dark:hover:border-brand-800/40 dark:hover:bg-brand-950/20 ${
              compact ? "px-3 py-2" : "px-4 py-3.5"
            }`}
            style={{ animationDelay: `${sourceIndex * 50}ms` }}
          >
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-100 dark:bg-brand-900/40">
                <FileText className="h-4 w-4 text-brand-600 dark:text-brand-400" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    {source.document_name}
                  </p>
                  {source.score > 0 && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-slate-200/80 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-400">
                      <Hash className="h-2.5 w-2.5" />
                      {formatPercent(source.score)}
                    </span>
                  )}
                </div>

                {source.citation_labels.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {source.citation_labels.map((label) => (
                      <span
                        key={label}
                        className="rounded-md bg-white px-2 py-0.5 text-[10px] font-medium text-slate-600 ring-1 ring-slate-200 dark:bg-slate-900 dark:text-slate-400 dark:ring-slate-700"
                      >
                        {label}
                      </span>
                    ))}
                  </div>
                )}

                {source.locations.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {source.locations.map((location, index) => {
                      const label = formatLocation(location);
                      if (!label) return null;
                      return (
                        <li
                          key={`${location.clause_number}-${location.page_number}-${index}`}
                          className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400"
                        >
                          <span className="h-1 w-1 shrink-0 rounded-full bg-brand-400" />
                          {label}
                        </li>
                      );
                    })}
                  </ul>
                )}

                {!compact && source.document_id && (
                  <Link
                    to={`/documents/${source.document_id}`}
                    className="mt-2.5 inline-flex items-center gap-1 text-xs font-medium text-brand-600 transition-colors hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300"
                  >
                    <ExternalLink className="h-3 w-3" />
                    View document
                  </Link>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

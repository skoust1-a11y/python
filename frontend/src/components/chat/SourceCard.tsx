import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, ChevronUp, ExternalLink, FileText } from "lucide-react";
import type { SourceCitation } from "@/api/types";
import { formatPercentPrecise } from "@/lib/utils";

interface SourceCardProps {
  source: SourceCitation;
  index: number;
}

function buildExcerpt(source: SourceCitation): string {
  if (source.citation_labels.length > 0) {
    return source.citation_labels.join(" · ");
  }

  const titles = source.locations
    .map((loc) => loc.clause_title)
    .filter((t): t is string => Boolean(t));

  if (titles.length > 0) {
    return titles.join(" · ");
  }

  const clauses = source.locations
    .map((loc) => (loc.clause_number ? `Clause ${loc.clause_number}` : null))
    .filter((c): c is string => Boolean(c));

  if (clauses.length > 0) {
    return `Referenced sections: ${clauses.join(", ")}. Open the document to view full clause text.`;
  }

  return "Source reference retrieved from document corpus. Expand to view location details.";
}

export function SourceCard({ source, index }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false);
  const excerpt = buildExcerpt(source);

  const primaryLocation = source.locations[0];

  return (
    <li
      className="animate-slide-up overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-sm transition-all duration-200 hover:border-brand-200/60 hover:shadow-md dark:border-slate-700/80 dark:bg-slate-900/60 dark:hover:border-brand-800/40"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="focus-ring flex w-full items-start gap-3 px-4 py-3.5 text-left"
        aria-expanded={expanded}
      >
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-100 dark:bg-brand-900/40">
          <FileText className="h-4 w-4 text-brand-600 dark:text-brand-400" />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {source.document_name}
            </p>
            {source.score > 0 && (
              <span className="shrink-0 rounded-full bg-emerald-100 px-2.5 py-0.5 text-[11px] font-semibold tabular-nums text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                {formatPercentPrecise(source.score)}
              </span>
            )}
          </div>

          <div className="mt-1.5 flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
            {primaryLocation?.clause_number && (
              <span className="rounded-md bg-slate-100 px-2 py-0.5 dark:bg-slate-800">
                Clause {primaryLocation.clause_number}
              </span>
            )}
            {primaryLocation?.page_number != null && (
              <span className="rounded-md bg-slate-100 px-2 py-0.5 dark:bg-slate-800">
                Page {primaryLocation.page_number}
              </span>
            )}
            {source.locations.length > 1 && (
              <span className="rounded-md bg-slate-100 px-2 py-0.5 dark:bg-slate-800">
                +{source.locations.length - 1} more
              </span>
            )}
          </div>
        </div>

        <span className="mt-1 shrink-0 text-slate-400">
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </span>
      </button>

      {expanded && (
        <div className="animate-fade-in border-t border-slate-100 px-4 py-3 dark:border-slate-800">
          <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">{excerpt}</p>

          {source.locations.length > 0 && (
            <ul className="mt-3 space-y-1.5">
              {source.locations.map((loc, locIndex) => (
                <li
                  key={`${loc.clause_number}-${loc.page_number}-${locIndex}`}
                  className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400"
                >
                  <span className="h-1 w-1 rounded-full bg-brand-400" />
                  {[
                    loc.clause_number ? `Clause ${loc.clause_number}` : null,
                    loc.clause_title,
                    loc.page_number != null ? `Page ${loc.page_number}` : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </li>
              ))}
            </ul>
          )}

          {source.citation_labels.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1">
              {source.citation_labels.map((label) => (
                <span
                  key={label}
                  className="rounded-md bg-brand-50 px-2 py-0.5 text-[10px] font-medium text-brand-700 ring-1 ring-brand-200/60 dark:bg-brand-950/40 dark:text-brand-300 dark:ring-brand-800/40"
                >
                  {label}
                </span>
              ))}
            </div>
          )}

          {source.document_id && (
            <Link
              to={`/documents/${source.document_id}`}
              className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400"
            >
              <ExternalLink className="h-3 w-3" />
              View full document
            </Link>
          )}
        </div>
      )}
    </li>
  );
}

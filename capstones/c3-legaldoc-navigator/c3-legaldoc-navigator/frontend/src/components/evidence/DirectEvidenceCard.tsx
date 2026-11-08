import { Link } from "react-router-dom";
import { ExternalLink, FileText } from "lucide-react";
import type { DirectEvidenceItem } from "@/api/types";
import { HighlightedChunkExcerpt } from "@/components/HighlightedChunkExcerpt";
import { directEvidenceMetadataBadges } from "@/lib/citationFormat";
import { formatPercentPrecise } from "@/lib/utils";

interface DirectEvidenceCardProps {
  item: DirectEvidenceItem;
  index?: number;
}

const MATCH_SOURCE_LABELS: Record<string, string> = {
  bm25: "Keyword",
  semantic: "Semantic",
};

function matchSourceBadges(sources: string[]): string[] {
  return sources.map((source) => MATCH_SOURCE_LABELS[source] ?? source);
}

export function DirectEvidenceCard({ item, index = 0 }: DirectEvidenceCardProps) {
  const badges = directEvidenceMetadataBadges(item);
  const highlights =
    item.highlights.length > 0
      ? item.highlights
      : [{ text: item.content, matched: false }];

  return (
    <li
      className="animate-slide-up overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-sm transition-all duration-200 hover:border-brand-200/60 hover:shadow-md dark:border-slate-700/80 dark:bg-slate-900/60 dark:hover:border-brand-800/40"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-start gap-3 px-4 py-3.5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-100 dark:bg-brand-900/40">
          <FileText className="h-4 w-4 text-brand-600 dark:text-brand-400" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {item.document}
            </p>
            {item.score > 0 && (
              <span className="shrink-0 rounded-full bg-emerald-100 px-2.5 py-0.5 text-[11px] font-semibold tabular-nums text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                {formatPercentPrecise(item.score)}
              </span>
            )}
          </div>

          {badges.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
              {badges.map((badge) => (
                <span
                  key={badge}
                  className="rounded-md bg-slate-100 px-2 py-0.5 dark:bg-slate-800"
                >
                  {badge}
                </span>
              ))}
            </div>
          )}

          {item.metadata.match_sources.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700 ring-1 ring-emerald-200/60 dark:bg-emerald-950/40 dark:text-emerald-300 dark:ring-emerald-800/40">
                {item.metadata.relevance_type === "direct" ? "Direct" : "Match"}
              </span>
              {matchSourceBadges(item.metadata.match_sources).map((label) => (
                <span
                  key={label}
                  className="rounded-md bg-brand-50 px-2 py-0.5 text-[10px] font-medium text-brand-700 ring-1 ring-brand-200/60 dark:bg-brand-950/40 dark:text-brand-300 dark:ring-brand-800/40"
                >
                  {label}
                </span>
              ))}
            </div>
          )}

          <div className="mt-3 border-t border-slate-100 pt-3 dark:border-slate-800">
            <HighlightedChunkExcerpt highlights={highlights} />
          </div>

          <Link
            to={`/documents/${item.metadata.document_id}`}
            className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-brand-600 transition-colors hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300"
          >
            <ExternalLink className="h-3 w-3" />
            View document
          </Link>
        </div>
      </div>
    </li>
  );
}

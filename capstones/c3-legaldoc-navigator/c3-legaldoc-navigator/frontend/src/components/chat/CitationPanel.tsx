import { BookOpen, X } from "lucide-react";
import type { SourceCitation } from "@/api/types";
import { SourcesList } from "@/components/SourcesList";
import { countRelevantClauses, countSourceDocuments } from "@/lib/sourceStats";

interface CitationPanelProps {
  sources: SourceCitation[];
  open: boolean;
  onClose: () => void;
  title?: string;
}

export function CitationPanel({ sources, open, onClose, title = "Citations" }: CitationPanelProps) {
  const docCount = countSourceDocuments(sources);
  const clauseCount = countRelevantClauses(sources);

  if (!open) return null;

  const panelContent = (
    <>
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-slate-200/80 px-4 py-3.5 dark:border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-100 dark:bg-brand-900/40">
            <BookOpen className="h-4 w-4 text-brand-600 dark:text-brand-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {docCount} {docCount === 1 ? "document" : "documents"}
              {clauseCount > 0 && (
                <>
                  {" "}
                  · {clauseCount} {clauseCount === 1 ? "clause" : "clauses"}
                </>
              )}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200 lg:hidden"
          aria-label="Close citations"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        <SourcesList sources={sources} variant="panel" />
      </div>
    </>
  );

  return (
    <>
      {/* Mobile overlay */}
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm lg:hidden"
        onClick={onClose}
        aria-hidden
      />

      {/* Panel — drawer on mobile, sticky sidebar on desktop */}
      <aside
        className="animate-slide-in-right fixed inset-y-0 right-0 z-50 flex w-full max-w-sm flex-col border-l border-slate-200/80 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-950 lg:static lg:z-auto lg:h-full lg:max-w-none lg:w-80 lg:shrink-0 lg:shadow-none xl:w-96"
        aria-label="Citation panel"
      >
        {panelContent}
      </aside>
    </>
  );
}

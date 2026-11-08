import { FileStack, Layers, Link2 } from "lucide-react";
import type { QueryResponse } from "@/api/types";
import { MessageActions } from "@/components/MessageActions";
import { MetricsPanel } from "@/components/chat/MetricsPanel";
import type { ResponseMetrics } from "@/lib/responseMetrics";
import { formatPercentPrecise } from "@/lib/utils";
import type { ResponseMode } from "@/lib/responseModes";

interface ResponseSidebarProps {
  response: QueryResponse;
  metrics: ResponseMetrics;
  activeMode: ResponseMode;
  answer: string;
  modeKey: string;
}

export function ResponseSidebar({
  response,
  metrics,
  activeMode,
  answer,
  modeKey,
}: ResponseSidebarProps) {
  return (
    <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
      <div className="hidden lg:block">
        <MetricsPanel metrics={metrics} modeKey={modeKey} />
      </div>
      <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-900/60">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Retrieval Summary
        </p>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg bg-slate-50 px-3 py-2.5 dark:bg-slate-800/60">
            <div className="flex items-center gap-1.5 text-slate-500">
              <FileStack className="h-3.5 w-3.5" />
              <span className="text-[10px] font-medium uppercase">Documents</span>
            </div>
            <p className="mt-1 text-xl font-bold tabular-nums text-slate-900 dark:text-slate-100">
              {metrics.documentCount}
            </p>
          </div>
          <div className="rounded-lg bg-slate-50 px-3 py-2.5 dark:bg-slate-800/60">
            <div className="flex items-center gap-1.5 text-slate-500">
              <Layers className="h-3.5 w-3.5" />
              <span className="text-[10px] font-medium uppercase">Clauses</span>
            </div>
            <p className="mt-1 text-xl font-bold tabular-nums text-slate-900 dark:text-slate-100">
              {metrics.clauseCount}
            </p>
          </div>
        </div>
      </div>

      {response.related_documents.length > 0 && (
        <div className="animate-fade-in rounded-xl border border-slate-200/80 bg-white p-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-900/60">
          <div className="mb-3 flex items-center gap-2">
            <Link2 className="h-4 w-4 text-slate-400" />
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Related Documents
            </p>
          </div>
          <ul className="space-y-2">
            {response.related_documents.map((doc) => (
              <li
                key={doc.document_id ?? doc.name}
                className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm dark:bg-slate-800/50"
              >
                <span className="truncate font-medium text-slate-800 dark:text-slate-200">
                  {doc.name}
                </span>
                <span className="shrink-0 text-xs font-semibold tabular-nums text-brand-600 dark:text-brand-400">
                  {formatPercentPrecise(doc.relevance)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-900/60">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Quick Actions
        </p>
        <MessageActions answer={answer} mode={activeMode} response={response} />
      </div>
    </aside>
  );
}

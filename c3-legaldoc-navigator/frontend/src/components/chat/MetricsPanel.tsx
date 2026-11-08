import { Clock, FileStack, Hash, Layers } from "lucide-react";
import type { ResponseMetrics } from "@/lib/responseMetrics";
import { formatLatency } from "@/lib/exportResponse";
import { formatPercentPrecise } from "@/lib/utils";

interface MetricsPanelProps {
  metrics: ResponseMetrics;
  modeKey?: string;
}

interface MetricBarProps {
  label: string;
  value: number;
  color: string;
  delay?: number;
}

function MetricBar({ label, value, color, delay = 0 }: MetricBarProps) {
  const pct = Math.min(100, Math.max(0, value * 100));

  return (
    <div className="min-w-0 space-y-1.5" style={{ animationDelay: `${delay}ms` }}>
      <div className="flex min-w-0 items-center justify-between gap-2">
        <span className="min-w-0 break-words text-xs font-medium leading-snug text-slate-600 dark:text-slate-400">
          {label}
        </span>
        <span className="shrink-0 text-sm font-semibold tabular-nums text-slate-900 dark:text-slate-100">
          {formatPercentPrecise(value)}
        </span>
      </div>
      <div className="h-2 w-full min-w-0 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function MetricsPanel({ metrics, modeKey }: MetricsPanelProps) {
  return (
    <div
      key={modeKey}
      className="animate-fade-in min-w-0 rounded-xl border border-slate-200/80 bg-gradient-to-br from-slate-50 to-white p-4 shadow-sm dark:border-slate-700/80 dark:from-slate-900/60 dark:to-slate-900"
    >
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
        AI Analysis Metrics
      </p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricBar label="Confidence" value={metrics.confidence} color="bg-emerald-500" delay={0} />
        <MetricBar
          label="Faithfulness"
          value={metrics.faithfulness}
          color="bg-brand-500"
          delay={60}
        />
        <MetricBar label="Relevance" value={metrics.relevance} color="bg-violet-500" delay={120} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 border-t border-slate-200/80 pt-4 sm:grid-cols-2 lg:grid-cols-4 dark:border-slate-700/80">
        <div className="flex min-w-0 items-center gap-2">
          <Clock className="h-4 w-4 shrink-0 text-slate-400" />
          <div className="min-w-0">
            <p className="break-words text-[10px] font-medium uppercase tracking-wide text-slate-500">
              Latency
            </p>
            <p className="text-sm font-semibold tabular-nums text-slate-800 dark:text-slate-200">
              {formatLatency(metrics.latencyMs)}
            </p>
          </div>
        </div>
        <div className="flex min-w-0 items-center gap-2">
          <FileStack className="h-4 w-4 shrink-0 text-slate-400" />
          <div className="min-w-0">
            <p className="break-words text-[10px] font-medium uppercase tracking-wide text-slate-500">
              Documents
            </p>
            <p className="text-sm font-semibold tabular-nums text-slate-800 dark:text-slate-200">
              {metrics.documentCount}
            </p>
          </div>
        </div>
        <div className="flex min-w-0 items-center gap-2">
          <Layers className="h-4 w-4 shrink-0 text-slate-400" />
          <div className="min-w-0">
            <p className="break-words text-[10px] font-medium uppercase tracking-wide text-slate-500">
              Clauses
            </p>
            <p className="text-sm font-semibold tabular-nums text-slate-800 dark:text-slate-200">
              {metrics.clauseCount}
            </p>
          </div>
        </div>
        <div className="flex min-w-0 items-center gap-2">
          <Hash className="h-4 w-4 shrink-0 text-slate-400" />
          <div className="min-w-0">
            <p className="break-words text-[10px] font-medium uppercase tracking-wide text-slate-500">
              Sources
            </p>
            <p className="text-sm font-semibold tabular-nums text-slate-800 dark:text-slate-200">
              {metrics.documentCount > 0 ? metrics.documentCount : "—"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

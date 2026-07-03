import { useMemo } from "react";
import { AlertTriangle, Bot, BookOpen } from "lucide-react";
import type { QueryResponse } from "@/api/types";
import { FollowUpChips } from "@/components/chat/FollowUpChips";
import { MarkdownAnswer } from "@/components/chat/MarkdownAnswer";
import { MetricsPanel } from "@/components/chat/MetricsPanel";
import { ResponseSidebar } from "@/components/chat/ResponseSidebar";
import { SourceCard } from "@/components/chat/SourceCard";
import { StickyModeSelector } from "@/components/chat/StickyModeSelector";
import { computeResponseMetrics } from "@/lib/responseMetrics";
import type { ResponseMode } from "@/lib/responseModes";

interface AssistantMessageProps {
  response: QueryResponse;
  activeMode: ResponseMode;
  latencyMs?: number;
  animate?: boolean;
  onModeChange: (mode: ResponseMode) => void;
  onFollowUp?: (question: string) => void;
  loading?: boolean;
}

export function AssistantMessage({
  response,
  activeMode,
  latencyMs,
  animate = false,
  onModeChange,
  onFollowUp,
  loading = false,
}: AssistantMessageProps) {
  const answer = response[activeMode];
  const metrics = useMemo(
    () => computeResponseMetrics(response, latencyMs),
    [response, latencyMs],
  );

  return (
    <div className="animate-slide-up w-full">
      <div className="flex items-start gap-3">
        <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 shadow-md shadow-brand-500/20 ring-2 ring-white dark:ring-slate-900">
          <Bot className="h-4 w-4 text-white" />
        </div>

        <div className="min-w-0 flex-1 space-y-4">
          <StickyModeSelector
            activeMode={activeMode}
            onModeChange={onModeChange}
            disabled={loading}
          />

          {/* Metrics — above answer (mobile); sidebar on desktop */}
          <div className="lg:hidden">
            <MetricsPanel metrics={metrics} modeKey={activeMode} />
          </div>

          {/* Two-column layout: answer + sources | stats sidebar */}
          <div className="grid gap-5 lg:grid-cols-[1fr_300px] xl:grid-cols-[1fr_320px] xl:gap-6">
            {/* Left — answer, follow-ups, sources */}
            <div className="min-w-0 space-y-4">
              <div className="glass-card overflow-hidden transition-shadow duration-300">
                <div className="border-b border-slate-100 px-5 py-3 dark:border-slate-800">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    AI Response
                  </p>
                </div>

                <div className="px-5 py-5">
                  <MarkdownAnswer text={answer} animate={animate} />
                </div>

                {response.verification_notice && (
                  <div className="mx-5 mb-5 flex items-start gap-2 rounded-xl border border-amber-200/80 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800/60 dark:bg-amber-900/20 dark:text-amber-200">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>{response.verification_notice}</span>
                  </div>
                )}
              </div>

              <FollowUpChips
                questions={response.follow_up_questions}
                onSelect={(q) => onFollowUp?.(q)}
                disabled={loading}
              />

              {response.sources.length > 0 && (
                <div>
                  <div className="mb-3 flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      Sources ({response.sources.length})
                    </p>
                  </div>
                  <ul className="space-y-3">
                    {response.sources.map((source, index) => (
                      <SourceCard
                        key={source.document_id ?? `${source.entity_type}-${source.entity_id}`}
                        source={source}
                        index={index}
                      />
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Right — document stats, related docs, quick actions */}
            <ResponseSidebar
              response={response}
              metrics={metrics}
              activeMode={activeMode}
              answer={answer}
              modeKey={activeMode}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

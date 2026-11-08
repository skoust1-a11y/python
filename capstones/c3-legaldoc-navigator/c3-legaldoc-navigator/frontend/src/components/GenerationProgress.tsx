import { Check, Circle, Loader2 } from "lucide-react";
import type { ProgressStep } from "@/hooks/useGenerationProgress";

interface GenerationProgressProps {
  steps: ProgressStep[];
  currentIndex: number;
}

export function GenerationProgress({ steps, currentIndex }: GenerationProgressProps) {
  return (
    <div className="space-y-4" aria-live="polite" aria-busy={currentIndex < steps.length - 1}>
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 animate-pulse-soft rounded-full bg-brand-500" />
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
          Analyzing documents…
        </p>
      </div>

      <ul className="space-y-2.5">
        {steps.map((step, index) => {
          const isComplete = index < currentIndex;
          const isCurrent = index === currentIndex;
          const isPending = index > currentIndex;

          return (
            <li
              key={step.id}
              className={`flex items-center gap-3 text-sm transition-all duration-300 ${
                isPending
                  ? "text-slate-400 dark:text-slate-600"
                  : isCurrent
                    ? "text-brand-700 dark:text-brand-300"
                    : "text-slate-600 dark:text-slate-400"
              }`}
              style={{
                transitionDelay: isCurrent ? "0ms" : `${index * 40}ms`,
              }}
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center">
                {isComplete ? (
                  <Check className="h-4 w-4 text-emerald-500 transition-transform duration-200" />
                ) : isCurrent ? (
                  <Loader2 className="h-4 w-4 animate-spin text-brand-600 dark:text-brand-400" />
                ) : (
                  <Circle className="h-3 w-3 text-slate-300 dark:text-slate-600" />
                )}
              </span>
              <span className={isCurrent ? "font-medium" : ""}>{step.label}</span>
              {isCurrent && (
                <span className="ml-auto h-1.5 w-16 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                  <span className="block h-full w-1/2 animate-shimmer rounded-full bg-brand-400/60" />
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

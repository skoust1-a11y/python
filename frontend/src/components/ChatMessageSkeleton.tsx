import { Loader2 } from "lucide-react";

interface ChatMessageSkeletonProps {
  label?: string;
}

export function ChatMessageSkeleton({
  label = "Retrieving and synthesizing...",
}: ChatMessageSkeletonProps) {
  return (
    <div className="space-y-3" aria-live="polite" aria-busy="true">
      <div className="space-y-2">
        <div className="h-3 w-[72%] animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
        <div className="h-3 w-full animate-pulse rounded-full bg-slate-200 dark:bg-slate-700 [animation-delay:150ms]" />
        <div className="h-3 w-[88%] animate-pulse rounded-full bg-slate-200 dark:bg-slate-700 [animation-delay:300ms]" />
        <div className="h-3 w-[60%] animate-pulse rounded-full bg-slate-200 dark:bg-slate-700 [animation-delay:450ms]" />
      </div>
      <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
        <Loader2 className="h-3.5 w-3.5 animate-spin text-brand-600 dark:text-brand-400" />
        <span>{label}</span>
      </div>
    </div>
  );
}

import { Loader2 } from "lucide-react";

interface LoadingStateProps {
  label?: string;
}

export function LoadingState({ label = "Loading..." }: LoadingStateProps) {
  return (
    <div
      className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-slate-500"
      role="status"
      aria-live="polite"
    >
      <Loader2 className="h-6 w-6 animate-spin text-brand-700" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

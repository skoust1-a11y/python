import { Sparkles } from "lucide-react";

const SUGGESTED_PROMPTS = [
  "What are the key termination clauses?",
  "Summarize liability and indemnification terms",
  "What notice period is required for contract changes?",
  "List obligations for both parties",
];

interface ChatEmptyStateProps {
  onSelectPrompt: (prompt: string) => void;
}

export function ChatEmptyState({ onSelectPrompt }: ChatEmptyStateProps) {
  return (
    <div className="animate-fade-in flex flex-col items-center py-12 text-center sm:py-16">
      <div className="animate-scale-in flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 shadow-xl shadow-brand-500/25 ring-1 ring-white/20">
        <Sparkles className="h-8 w-8 text-white" />
      </div>
      <h3 className="mt-6 text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
        Ask about your legal documents
      </h3>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-slate-500 dark:text-slate-400">
        Get evidence-based answers with source citations, confidence scores, and multiple
        analysis modes — all from a single retrieval.
      </p>
      <div className="stagger-children mt-8 flex max-w-lg flex-wrap justify-center gap-2">
        {SUGGESTED_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onSelectPrompt(prompt)}
            className="focus-ring rounded-full border border-slate-200/80 bg-white px-4 py-2.5 text-xs font-medium text-slate-700 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 hover:shadow-md dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-brand-700 dark:hover:bg-brand-950/50 dark:hover:text-brand-300"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

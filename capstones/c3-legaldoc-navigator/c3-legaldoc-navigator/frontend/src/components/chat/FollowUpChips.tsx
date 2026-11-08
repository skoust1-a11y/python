import { MessageCircleQuestion } from "lucide-react";

interface FollowUpChipsProps {
  questions: string[];
  onSelect: (question: string) => void;
  disabled?: boolean;
}

export function FollowUpChips({ questions, onSelect, disabled = false }: FollowUpChipsProps) {
  if (questions.length === 0) return null;

  return (
    <div className="animate-fade-in mt-5">
      <div className="mb-2.5 flex items-center gap-2">
        <MessageCircleQuestion className="h-4 w-4 text-slate-400" />
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Suggested follow-ups
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {questions.map((question, index) => (
          <button
            key={question}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(question)}
            className="focus-ring animate-slide-up rounded-full border border-slate-200/80 bg-white px-4 py-2 text-left text-xs font-medium text-slate-700 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 hover:shadow-md disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-brand-700 dark:hover:bg-brand-950/40 dark:hover:text-brand-300"
            style={{ animationDelay: `${index * 50}ms` }}
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}

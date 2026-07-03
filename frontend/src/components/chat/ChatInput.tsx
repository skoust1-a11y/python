import { useEffect, useRef } from "react";
import { Loader2, Send } from "lucide-react";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  loading?: boolean;
  placeholder?: string;
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  loading = false,
  placeholder = "Ask about clauses, contracts, obligations...",
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="glass-surface shrink-0 border-t px-4 py-4 lg:px-6">
      <div className="mx-auto max-w-6xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit();
          }}
          className="relative flex items-end gap-2 rounded-2xl border border-slate-200/80 bg-white p-2 shadow-lg shadow-slate-900/5 transition-all duration-200 focus-within:border-brand-400 focus-within:shadow-brand-500/10 dark:border-slate-700/80 dark:bg-slate-900 dark:shadow-black/20 dark:focus-within:border-brand-600"
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={loading}
            rows={1}
            className="max-h-40 min-h-[44px] flex-1 resize-none bg-transparent px-3 py-2.5 text-sm outline-none placeholder:text-slate-400 disabled:opacity-50 dark:placeholder:text-slate-500"
          />
          <button
            type="submit"
            disabled={loading || !value.trim()}
            className="focus-ring mb-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-600 to-brand-700 text-white shadow-md shadow-brand-600/25 transition-all duration-200 hover:from-brand-500 hover:to-brand-600 hover:shadow-lg disabled:opacity-40 disabled:shadow-none"
            title="Send message"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </form>

        <p className="mt-2 text-center text-[11px] text-slate-400 dark:text-slate-500">
          Enter to send · Shift+Enter for new line · Modes switch per response above
        </p>
      </div>
    </div>
  );
}

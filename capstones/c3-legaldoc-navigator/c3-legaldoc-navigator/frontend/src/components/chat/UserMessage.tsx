import { User } from "lucide-react";

interface UserMessageProps {
  content: string;
}

export function UserMessage({ content }: UserMessageProps) {
  return (
    <div className="animate-slide-up flex justify-end">
      <div className="flex max-w-[85%] items-start gap-3 sm:max-w-[75%]">
        <div className="rounded-2xl rounded-tr-md bg-gradient-to-br from-brand-600 to-brand-700 px-5 py-3.5 text-[15px] leading-relaxed text-white shadow-md shadow-brand-600/15 ring-1 ring-white/10">
          {content}
        </div>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-200 ring-2 ring-white dark:bg-slate-700 dark:ring-slate-900">
          <User className="h-4 w-4 text-slate-600 dark:text-slate-300" />
        </div>
      </div>
    </div>
  );
}

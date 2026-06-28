import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  title?: string;
  action?: ReactNode;
}

export function Card({ children, className = "", title, action }: CardProps) {
  return (
    <div
      className={`rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900 ${className}`}
    >
      {(title || action) && (
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          {title && <h3 className="font-semibold text-slate-900 dark:text-slate-100">{title}</h3>}
          {action}
        </div>
      )}
      <div className={title || action ? "p-5" : "p-5"}>{children}</div>
    </div>
  );
}

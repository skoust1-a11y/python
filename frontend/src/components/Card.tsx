import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  title?: string;
  action?: ReactNode;
}

export function Card({ children, className = "", title, action }: CardProps) {
  return (
    <section
      className={`rounded-lg border border-slate-200 bg-white ${className}`}
    >
      {(title || action) && (
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          {title ? <h3 className="text-sm font-semibold text-slate-900">{title}</h3> : <span />}
          {action}
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

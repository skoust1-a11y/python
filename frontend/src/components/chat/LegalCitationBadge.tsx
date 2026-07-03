interface LegalCitationBadgeProps {
  label: string;
  variant?: "source" | "reference";
}

export function LegalCitationBadge({ label, variant = "source" }: LegalCitationBadgeProps) {
  const isSource = variant === "source" || /^\[(?:Source|S)\s*\d+\]$/i.test(label);

  return (
    <span
      className={`legal-citation-badge mx-0.5 inline-flex items-center rounded-md px-1.5 py-px text-[11px] font-semibold leading-tight tracking-wide whitespace-nowrap align-baseline ${
        isSource
          ? "bg-brand-100 text-brand-800 ring-1 ring-brand-200/70 dark:bg-brand-900/45 dark:text-brand-200 dark:ring-brand-700/50"
          : "bg-violet-100 text-violet-800 ring-1 ring-violet-200/70 dark:bg-violet-900/40 dark:text-violet-200 dark:ring-violet-700/50"
      }`}
      title="Legal citation"
    >
      {label}
    </span>
  );
}

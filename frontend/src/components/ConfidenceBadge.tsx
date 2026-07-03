import { Shield, ShieldAlert, ShieldCheck } from "lucide-react";
import { confidenceLevelColor, formatPercent } from "@/lib/utils";

interface ConfidenceBadgeProps {
  level: "High" | "Medium" | "Low";
  score?: number;
  size?: "sm" | "md";
}

const LEVEL_ICONS = {
  High: ShieldCheck,
  Medium: Shield,
  Low: ShieldAlert,
} as const;

export function ConfidenceBadge({ level, score, size = "sm" }: ConfidenceBadgeProps) {
  const Icon = LEVEL_ICONS[level];
  const sizeClasses = size === "md" ? "px-3 py-1 text-sm" : "px-2.5 py-0.5 text-xs";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold shadow-sm ${sizeClasses} ${confidenceLevelColor(level)}`}
      title={score != null ? `${formatPercent(score)} confidence` : undefined}
    >
      <Icon className={size === "md" ? "h-4 w-4" : "h-3 w-3"} />
      <span>{level}</span>
      {score != null && (
        <span className="font-normal opacity-80">· {formatPercent(score)}</span>
      )}
    </span>
  );
}

import { Gauge } from "lucide-react";
import { confidenceColor, formatPercent } from "@/lib/utils";

interface ConfidenceScoreProps {
  score: number;
  label?: string;
  size?: "sm" | "md" | "lg";
}

export function ConfidenceScore({ score, label = "Confidence", size = "md" }: ConfidenceScoreProps) {
  const pct = Math.round(score * 100);
  const color = confidenceColor(score);

  const ringSize = size === "sm" ? 48 : size === "lg" ? 80 : 64;
  const stroke = size === "sm" ? 4 : 5;
  const radius = (ringSize - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score * circumference);

  return (
    <div className="flex items-center gap-3">
      <div className="relative" style={{ width: ringSize, height: ringSize }}>
        <svg width={ringSize} height={ringSize} className="-rotate-90">
          <circle
            cx={ringSize / 2}
            cy={ringSize / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={stroke}
            className="text-slate-200 dark:text-slate-700"
          />
          <circle
            cx={ringSize / 2}
            cy={ringSize / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={stroke}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={color}
          />
        </svg>
        <span
          className={`absolute inset-0 flex items-center justify-center font-semibold ${color} ${
            size === "sm" ? "text-xs" : size === "lg" ? "text-lg" : "text-sm"
          }`}
        >
          {pct}%
        </span>
      </div>
      <div>
        <div className="flex items-center gap-1.5">
          <Gauge className="h-4 w-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{label}</span>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">{formatPercent(score)} retrieval match</p>
      </div>
    </div>
  );
}

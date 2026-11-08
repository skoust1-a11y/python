import { GitBranch, Info } from "lucide-react";
import type { RoutingMetadata } from "@/api/types";
import { Badge } from "./Badge";
import { formatPercent, routeLabel } from "@/lib/utils";

interface RouteBadgeProps {
  routing: RoutingMetadata;
}

export function RouteBadge({ routing }: RouteBadgeProps) {
  const variant =
    routing.route === "rag" ? "info" : routing.route === "sql" ? "warning" : "success";

  return (
    <div className="flex flex-wrap items-start gap-3">
      <div className="flex items-center gap-2">
        <GitBranch className="h-4 w-4 text-slate-400" />
        <Badge variant={variant}>{routeLabel(routing.route)}</Badge>
        <span className="text-xs text-slate-500 dark:text-slate-400">
          Routing confidence: {formatPercent(routing.confidence)}
        </span>
      </div>
      <p className="flex w-full items-start gap-1.5 text-sm text-slate-600 dark:text-slate-400">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        {routing.reason}
      </p>
    </div>
  );
}

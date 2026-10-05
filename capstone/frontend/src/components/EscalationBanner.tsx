import type { QueryResponse } from "../api/types";

export function EscalationBanner({ escalation, outcome }: { escalation: QueryResponse["escalation"]; outcome: string }) {
  if (outcome !== "escalated" && !escalation.required) return null;
  return (
    <div className="banner">
      <strong>Human review required</strong>
      <p>{escalation.reason}</p>
      <p>
        Reviewer: {escalation.recommended_reviewer || "—"} · Triggers: {escalation.triggers.join(", ") || "—"}
      </p>
    </div>
  );
}

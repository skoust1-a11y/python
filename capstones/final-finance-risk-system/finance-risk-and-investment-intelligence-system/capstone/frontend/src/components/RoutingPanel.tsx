import type { QueryResponse } from "../api/types";

export function RoutingPanel({ routing, evidenceMode }: { routing: QueryResponse["routing"]; evidenceMode: string }) {
  return (
    <dl className="panel">
      <div>
        <dt>Category</dt>
        <dd>
          {routing.category_label} <span className="muted">{routing.category}</span>
        </dd>
      </div>
      <div>
        <dt>Agents</dt>
        <dd>{routing.agents_used.join(" → ")}</dd>
      </div>
      <div>
        <dt>Confidence</dt>
        <dd>{(routing.confidence * 100).toFixed(0)}%</dd>
      </div>
      <div>
        <dt>Evidence</dt>
        <dd>{evidenceMode}</dd>
      </div>
      {routing.rationale && (
        <div>
          <dt>Why</dt>
          <dd>{routing.rationale}</dd>
        </div>
      )}
    </dl>
  );
}

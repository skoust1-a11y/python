import type { QueryResponse } from "@/api/types";
import { Card } from "./Card";
import { ConfidenceScore } from "./ConfidenceScore";
import { RouteBadge } from "./RouteBadge";
import { RetrievedChunks, SourcesList } from "./SourcesList";

interface QueryResultPanelProps {
  response: QueryResponse;
  showChunks?: boolean;
}

export function QueryResultPanel({ response, showChunks = true }: QueryResultPanelProps) {
  return (
    <div className="space-y-4">
      <Card title="Answer">
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800 dark:text-slate-200">
          {response.answer}
        </p>
        {response.explanation && (
          <p className="mt-3 border-t border-slate-200 pt-3 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
            {response.explanation}
          </p>
        )}
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Route Used">
          <RouteBadge routing={response.routing} />
        </Card>
        <Card title="Confidence">
          <ConfidenceScore score={response.confidence_score} size="lg" />
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
            <span>Provider: {response.provider}</span>
            <span>•</span>
            <span>Retrieved: {response.retrieved_count}</span>
          </div>
        </Card>
      </div>

      {showChunks ? (
        <Card title="Retrieved Chunks">
          <RetrievedChunks
            sources={response.sources}
            vectorCount={response.vector_count}
            sqlCount={response.sql_count}
          />
        </Card>
      ) : (
        <Card title="Sources">
          <SourcesList sources={response.sources} />
        </Card>
      )}

      {response.structured_metadata && response.structured_metadata.total_count > 0 && (
        <Card title="Structured Metadata">
          <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">
            {response.structured_metadata.plan_explanation ?? "SQL/hybrid structured results"}
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: "Contracts", count: response.structured_metadata.contracts.length },
              { label: "Clauses", count: response.structured_metadata.clauses.length },
              { label: "Cases", count: response.structured_metadata.cases.length },
              { label: "Records", count: response.structured_metadata.metadata_records.length },
            ].map((item) => (
              <div
                key={item.label}
                className="rounded-lg bg-slate-50 p-3 text-center dark:bg-slate-800"
              >
                <p className="text-2xl font-bold text-brand-600 dark:text-brand-400">{item.count}</p>
                <p className="text-xs text-slate-500">{item.label}</p>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

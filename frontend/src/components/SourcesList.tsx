import { BookOpen, Database, FileText, Layers } from "lucide-react";
import type { SourceCitation } from "@/api/types";
import { Badge } from "./Badge";
import { formatPercent } from "@/lib/utils";

interface SourcesListProps {
  sources: SourceCitation[];
  compact?: boolean;
}

function sourceIcon(type: string) {
  if (type.startsWith("sql")) return Database;
  if (type === "vector") return Layers;
  return FileText;
}

export function SourcesList({ sources, compact = false }: SourcesListProps) {
  if (sources.length === 0) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400">No sources retrieved.</p>
    );
  }

  return (
    <div className="space-y-3">
      {sources.map((source, i) => {
        const Icon = sourceIcon(source.source_type);
        return (
          <div
            key={`${source.document_id}-${source.chunk_index}-${i}`}
            className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/50"
          >
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Icon className="h-4 w-4 text-brand-600 dark:text-brand-400" />
              <Badge variant="info">{source.source_type}</Badge>
              {source.citation_label && (
                <span className="text-xs font-medium text-brand-700 dark:text-brand-300">
                  {source.citation_label}
                </span>
              )}
              <span className="ml-auto text-xs font-medium text-slate-500">
                Score: {formatPercent(source.score)}
              </span>
            </div>
            {!compact && (
              <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                {source.excerpt}
              </p>
            )}
            {compact && (
              <p className="line-clamp-2 text-sm text-slate-600 dark:text-slate-400">
                {source.excerpt}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

interface RetrievedChunksProps {
  sources: SourceCitation[];
  vectorCount: number;
  sqlCount: number;
}

export function RetrievedChunks({ sources, vectorCount, sqlCount }: RetrievedChunksProps) {
  const vectorSources = sources.filter((s) => s.source_type === "vector");
  const sqlSources = sources.filter((s) => s.source_type.startsWith("sql"));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 text-sm">
        <div className="flex items-center gap-2 rounded-lg bg-brand-50 px-3 py-2 dark:bg-brand-900/20">
          <Layers className="h-4 w-4 text-brand-600 dark:text-brand-400" />
          <span className="font-medium">{vectorCount} vector chunk{vectorCount !== 1 ? "s" : ""}</span>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 dark:bg-amber-900/20">
          <Database className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          <span className="font-medium">{sqlCount} SQL result{sqlCount !== 1 ? "s" : ""}</span>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 dark:bg-slate-800">
          <BookOpen className="h-4 w-4 text-slate-500" />
          <span className="font-medium">{sources.length} total source{sources.length !== 1 ? "s" : ""}</span>
        </div>
      </div>

      {vectorSources.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
            Vector Chunks
          </h4>
          <div className="space-y-2">
            {vectorSources.map((chunk, i) => (
              <div
                key={`chunk-${chunk.chunk_index}-${i}`}
                className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
              >
                <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
                  <span>Chunk #{chunk.chunk_index ?? i + 1}</span>
                  <span>{formatPercent(chunk.score)}</span>
                </div>
                <p className="text-sm text-slate-700 dark:text-slate-300">{chunk.excerpt}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {sqlSources.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
            SQL Results
          </h4>
          <SourcesList sources={sqlSources} />
        </div>
      )}
    </div>
  );
}

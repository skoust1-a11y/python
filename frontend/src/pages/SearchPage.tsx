import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search as SearchIcon, SlidersHorizontal } from "lucide-react";
import { listDocuments, queryDocuments } from "@/api/client";
import type { DocumentSummary, QueryResponse } from "@/api/types";
import { Card } from "@/components/Card";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { QueryResultPanel } from "@/components/QueryResultPanel";
import { loadStoredResponseMode, storeResponseMode, type ResponseMode } from "@/lib/responseModes";

export function SearchPage() {
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState("");
  const [documentId, setDocumentId] = useState(searchParams.get("doc") ?? "");
  const [topK, setTopK] = useState(5);
  const [threshold, setThreshold] = useState(0.7);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [activeMode, setActiveMode] = useState<ResponseMode>(loadStoredResponseMode);

  useEffect(() => {
    listDocuments(0, 100)
      .then((res) => setDocuments(res.items))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const doc = searchParams.get("doc");
    if (doc) setDocumentId(doc);
  }, [searchParams]);

  const handleModeChange = (mode: ResponseMode) => {
    setActiveMode(mode);
    storeResponseMode(mode);
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const question = query.trim();
    if (!question) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await queryDocuments({
        question,
        document_id: documentId || null,
        top_k: topK,
        similarity_threshold: threshold,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Search</h2>
        <p className="mt-1 text-slate-500 dark:text-slate-400">
          Semantic search across your legal document corpus
        </p>
      </div>

      <Card>
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="relative">
            <SearchIcon className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for clauses, terms, parties, obligations..."
              className="w-full rounded-lg border border-slate-300 bg-white py-3 pl-10 pr-4 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div className="flex flex-wrap items-end gap-4">
            <div className="min-w-[200px] flex-1">
              <label className="mb-1 block text-xs font-medium text-slate-500">
                Document scope
              </label>
              <select
                value={documentId}
                onChange={(e) => setDocumentId(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
              >
                <option value="">All documents</option>
                {documents.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.title ?? doc.filename}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              onClick={() => setShowAdvanced((s) => !s)}
              className="flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
            >
              <SlidersHorizontal className="h-4 w-4" />
              Advanced
            </button>

            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="rounded-lg bg-brand-600 px-6 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              Search
            </button>
          </div>

          {showAdvanced && (
            <div className="grid gap-4 rounded-lg bg-slate-50 p-4 sm:grid-cols-2 dark:bg-slate-800/50">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-500">
                  Top K chunks ({topK})
                </label>
                <input
                  type="range"
                  min={1}
                  max={20}
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  className="w-full"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-500">
                  Similarity threshold ({threshold.toFixed(2)})
                </label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={threshold}
                  onChange={(e) => setThreshold(Number(e.target.value))}
                  className="w-full"
                />
              </div>
            </div>
          )}
        </form>
      </Card>

      {loading && (
        <Card>
          <LoadingSpinner size="lg" label="Searching documents and retrieving chunks..." />
        </Card>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      {result && !loading && (
        <QueryResultPanel
          response={result}
          activeMode={activeMode}
          onModeChange={handleModeChange}
        />
      )}
    </div>
  );
}

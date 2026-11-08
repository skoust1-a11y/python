import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search as SearchIcon, SlidersHorizontal } from "lucide-react";
import { keywordSearchDocuments, listDocuments } from "@/api/client";
import type { DocumentSummary, KeywordSearchResponse } from "@/api/types";
import { Card } from "@/components/Card";
import { DirectEvidenceResults } from "@/components/evidence/DirectEvidenceResults";
import { LoadingSpinner } from "@/components/LoadingSpinner";

export function SearchPage() {
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState("");
  const [documentId, setDocumentId] = useState(searchParams.get("doc") ?? "");
  const [topK, setTopK] = useState(10);
  const [exactPhrase, setExactPhrase] = useState(false);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<KeywordSearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    listDocuments(0, 100)
      .then((res) => setDocuments(res.items))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const doc = searchParams.get("doc");
    if (doc) setDocumentId(doc);
  }, [searchParams]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const searchQuery = query.trim();
    if (!searchQuery) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await keywordSearchDocuments({
        query: searchQuery,
        document_id: documentId || null,
        top_k: topK,
        exact_phrase: exactPhrase,
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
          Hybrid keyword + semantic search over indexed documents
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
              placeholder="e.g. tell me about payment terms, termination clause..."
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
                  Top K matches ({topK})
                </label>
                <input
                  type="range"
                  min={1}
                  max={50}
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  className="w-full"
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={exactPhrase}
                  onChange={(e) => setExactPhrase(e.target.checked)}
                  className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                />
                Exact phrase match
              </label>
            </div>
          )}
        </form>
      </Card>

      {loading && (
        <Card>
          <LoadingSpinner size="lg" label="Searching documents..." />
        </Card>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      {result && !loading && (
        <Card title={`Results for "${result.query}"`}>
          <DirectEvidenceResults
            results={result.results}
            totalCandidates={result.total_candidates}
            latencyMs={result.latency_ms}
            bm25HitCount={result.bm25_hit_count}
            semanticHitCount={result.semantic_hit_count}
          />
        </Card>
      )}
    </div>
  );
}

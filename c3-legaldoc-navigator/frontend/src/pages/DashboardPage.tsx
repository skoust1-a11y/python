import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, FileText, Layers, Upload, ArrowRight } from "lucide-react";
import { getHealth, listDocuments } from "@/api/client";
import type { DocumentSummary, HealthResponse } from "@/api/types";
import { Card } from "@/components/Card";
import { PageLoader } from "@/components/LoadingSpinner";
import { formatDate, statusColor } from "@/lib/utils";

export function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [healthRes, docsRes] = await Promise.all([
          getHealth(),
          listDocuments(0, 10),
        ]);
        setHealth(healthRes);
        setDocuments(docsRes.items);
        setTotal(docsRes.total);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <PageLoader label="Loading dashboard..." />;
  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-300">
        <p className="font-medium">Unable to connect to API</p>
        <p className="mt-1 text-sm">{error}</p>
        <p className="mt-3 text-sm">Ensure the backend is running on port 8000.</p>
      </div>
    );
  }

  const indexed = documents.filter((d) => d.status === "indexed").length;
  const totalChunks = documents.reduce((sum, d) => sum + (d.chunk_count ?? 0), 0);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Dashboard</h2>
        <p className="mt-1 text-slate-500 dark:text-slate-400">
          Overview of your legal document knowledge base
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <div className="flex items-center gap-4">
            <div className="rounded-lg bg-emerald-100 p-3 dark:bg-emerald-900/30">
              <Activity className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <p className="text-sm text-slate-500">API Status</p>
              <p className="text-xl font-bold capitalize">{health?.status}</p>
              <p className="text-xs text-slate-400">v{health?.version}</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="rounded-lg bg-brand-100 p-3 dark:bg-brand-900/30">
              <FileText className="h-6 w-6 text-brand-600 dark:text-brand-400" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Documents</p>
              <p className="text-xl font-bold">{total}</p>
              <p className="text-xs text-slate-400">{indexed} indexed</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="rounded-lg bg-violet-100 p-3 dark:bg-violet-900/30">
              <Layers className="h-6 w-6 text-violet-600 dark:text-violet-400" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Chunks (recent)</p>
              <p className="text-xl font-bold">{totalChunks}</p>
              <p className="text-xs text-slate-400">From last 10 docs</p>
            </div>
          </div>
        </Card>

        <Card>
          <Link
            to="/upload"
            className="flex items-center gap-4 transition-opacity hover:opacity-80"
          >
            <div className="rounded-lg bg-amber-100 p-3 dark:bg-amber-900/30">
              <Upload className="h-6 w-6 text-amber-600 dark:text-amber-400" />
            </div>
            <div className="flex-1">
              <p className="text-sm text-slate-500">Quick action</p>
              <p className="font-semibold">Upload document</p>
            </div>
            <ArrowRight className="h-5 w-5 text-slate-400" />
          </Link>
        </Card>
      </div>

      <Card title="Recent Documents">
        {documents.length === 0 ? (
          <div className="py-8 text-center">
            <p className="text-slate-500">No documents yet.</p>
            <Link
              to="/upload"
              className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-brand-600 hover:underline dark:text-brand-400"
            >
              Upload your first document <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-700">
                  <th className="pb-3 pr-4 font-medium">Title</th>
                  <th className="pb-3 pr-4 font-medium">Type</th>
                  <th className="pb-3 pr-4 font-medium">Status</th>
                  <th className="pb-3 pr-4 font-medium">Chunks</th>
                  <th className="pb-3 font-medium">Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr
                    key={doc.id}
                    className="border-b border-slate-100 dark:border-slate-800"
                  >
                    <td className="py-3 pr-4">
                      <Link
                        to={`/documents/${doc.id}`}
                        className="font-medium text-brand-600 hover:underline dark:text-brand-400"
                      >
                        {doc.title ?? doc.filename}
                      </Link>
                    </td>
                    <td className="py-3 pr-4 uppercase text-slate-500">{doc.file_type}</td>
                    <td className="py-3 pr-4">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(doc.status)}`}>
                        {doc.status}
                      </span>
                    </td>
                    <td className="py-3 pr-4">{doc.chunk_count ?? "—"}</td>
                    <td className="py-3 text-slate-500">{formatDate(doc.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

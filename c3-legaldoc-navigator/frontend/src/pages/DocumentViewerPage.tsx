import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  FileText,
  Calendar,
  Users,
  Hash,
  Tag,
  ArrowLeft,
  Layers,
} from "lucide-react";
import { getDocument, listDocuments } from "@/api/client";
import type { DocumentDetailResponse, DocumentSummary } from "@/api/types";
import { Card } from "@/components/Card";
import { PageLoader } from "@/components/LoadingSpinner";
import { Badge } from "@/components/Badge";
import { formatBytes, formatDate, statusColor } from "@/lib/utils";

function MetadataRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
}) {
  if (!value || value === "—") return null;
  return (
    <div className="flex items-start gap-3">
      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
      <div>
        <p className="text-xs font-medium text-slate-500">{label}</p>
        <p className="text-sm text-slate-800 dark:text-slate-200">{value}</p>
      </div>
    </div>
  );
}

function DocumentDetail({ doc }: { doc: DocumentDetailResponse }) {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {doc.title ?? doc.filename}
          </h2>
          <p className="mt-1 text-sm text-slate-500">{doc.filename}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-sm font-medium ${statusColor(doc.status)}`}>
          {doc.status}
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Document Info" className="lg:col-span-1">
          <div className="space-y-4">
            <MetadataRow icon={FileText} label="File type" value={doc.file_type.toUpperCase()} />
            <MetadataRow icon={Layers} label="Chunks" value={doc.chunk_count ?? "—"} />
            <MetadataRow icon={Hash} label="Pages" value={doc.page_count ?? "—"} />
            <MetadataRow icon={Hash} label="Size" value={formatBytes(doc.file_size_bytes)} />
            <MetadataRow icon={Calendar} label="Document date" value={doc.document_date ?? "—"} />
            <MetadataRow icon={Calendar} label="Uploaded" value={formatDate(doc.created_at)} />
            <MetadataRow icon={Tag} label="Contract ID" value={doc.contract_id ?? "—"} />
            <MetadataRow icon={Tag} label="Subtype" value={doc.document_subtype ?? "—"} />
            {doc.parties_involved && doc.parties_involved.length > 0 && (
              <MetadataRow
                icon={Users}
                label="Parties"
                value={doc.parties_involved.join(", ")}
              />
            )}
          </div>
        </Card>

        <div className="space-y-4 lg:col-span-2">
          {doc.summary && (
            <Card title="Summary">
              <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                {doc.summary}
              </p>
            </Card>
          )}

          {doc.keywords && doc.keywords.length > 0 && (
            <Card title="Keywords">
              <div className="flex flex-wrap gap-2">
                {doc.keywords.map((kw) => (
                  <Badge key={kw} variant="info">
                    {kw}
                  </Badge>
                ))}
              </div>
            </Card>
          )}

          {doc.doc_metadata && Object.keys(doc.doc_metadata).length > 0 && (
            <Card title="Additional Metadata">
              <pre className="overflow-x-auto rounded-lg bg-slate-50 p-4 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                {JSON.stringify(doc.doc_metadata, null, 2)}
              </pre>
            </Card>
          )}

          <Card title="Actions">
            <p className="mb-3 text-sm text-slate-500">
              Query this document in Chat or Search to view answers and source citations.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                to={`/chat?doc=${doc.id}`}
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
              >
                Chat about this document
              </Link>
              <Link
                to={`/search?doc=${doc.id}`}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                Search this document
              </Link>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

export function DocumentViewerPage() {
  const { id } = useParams<{ id: string }>();
  const [doc, setDoc] = useState<DocumentDetailResponse | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        if (id) {
          const detail = await getDocument(id);
          setDoc(detail);
        } else {
          const list = await listDocuments(0, 50);
          setDocuments(list.items);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load document");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) return <PageLoader label="Loading document..." />;

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-700 dark:border-red-900 dark:bg-red-900/20 dark:text-red-300">
        {error}
        <Link to="/documents" className="mt-3 block text-sm underline">
          Back to documents
        </Link>
      </div>
    );
  }

  if (!id) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Document Viewer</h2>
          <p className="mt-1 text-slate-500">Select a document to view its metadata</p>
        </div>

        {documents.length === 0 ? (
          <Card>
            <p className="py-8 text-center text-slate-500">No documents available.</p>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {documents.map((d) => (
              <Link key={d.id} to={`/documents/${d.id}`}>
                <Card className="h-full transition-shadow hover:shadow-md">
                  <div className="flex items-start gap-3">
                    <FileText className="h-8 w-8 shrink-0 text-brand-600 dark:text-brand-400" />
                    <div className="min-w-0">
                      <p className="truncate font-semibold">{d.title ?? d.filename}</p>
                      <p className="text-xs uppercase text-slate-500">{d.file_type}</p>
                      <span className={`mt-2 inline-block rounded-full px-2 py-0.5 text-xs ${statusColor(d.status)}`}>
                        {d.status}
                      </span>
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (!doc) return null;

  return (
    <div className="space-y-4">
      <Link
        to="/documents"
        className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600 dark:hover:text-brand-400"
      >
        <ArrowLeft className="h-4 w-4" /> All documents
      </Link>
      <DocumentDetail doc={doc} />
    </div>
  );
}

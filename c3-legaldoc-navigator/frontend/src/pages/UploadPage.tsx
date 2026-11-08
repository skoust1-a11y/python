import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Upload as UploadIcon, File, CheckCircle, AlertCircle } from "lucide-react";
import { uploadDocument } from "@/api/client";
import type { DocumentUploadResponse } from "@/api/types";
import { Card } from "@/components/Card";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { formatDate } from "@/lib/utils";

const ACCEPTED = ".pdf,.docx,.txt";

export function UploadPage() {
  const navigate = useNavigate();
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DocumentUploadResponse | null>(null);

  const handleFile = useCallback(async (file: File) => {
    setError(null);
    setResult(null);
    setUploading(true);
    setProgress(0);

    try {
      const res = await uploadDocument(file, setProgress);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const onFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Upload Documents</h2>
        <p className="mt-1 text-slate-500 dark:text-slate-400">
          Upload PDF, DOCX, or TXT files for indexing and retrieval
        </p>
      </div>

      <Card>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={`relative rounded-xl border-2 border-dashed p-12 text-center transition-colors ${
            dragging
              ? "border-brand-500 bg-brand-50 dark:bg-brand-900/20"
              : "border-slate-300 dark:border-slate-700"
          }`}
        >
          {uploading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center rounded-xl bg-white/90 dark:bg-slate-900/90">
              <LoadingSpinner label={`Uploading... ${progress}%`} />
              <div className="mt-4 h-2 w-48 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                <div
                  className="h-full bg-brand-600 transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          <UploadIcon className="mx-auto h-12 w-12 text-slate-400" />
          <p className="mt-4 font-medium text-slate-700 dark:text-slate-300">
            Drag and drop your file here
          </p>
          <p className="mt-1 text-sm text-slate-500">or</p>
          <label className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700">
            <File className="h-4 w-4" />
            Browse files
            <input
              type="file"
              accept={ACCEPTED}
              className="hidden"
              onChange={onFileSelect}
              disabled={uploading}
            />
          </label>
          <p className="mt-4 text-xs text-slate-400">PDF, DOCX, TXT — max 50 MB</p>
        </div>
      </Card>

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-900/20">
          <AlertCircle className="h-5 w-5 shrink-0 text-red-600" />
          <div>
            <p className="font-medium text-red-700 dark:text-red-300">Upload failed</p>
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </div>
        </div>
      )}

      {result && (
        <div className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-900 dark:bg-emerald-900/20">
          <CheckCircle className="h-5 w-5 shrink-0 text-emerald-600" />
          <div className="flex-1">
            <p className="font-medium text-emerald-700 dark:text-emerald-300">Upload successful</p>
            <dl className="mt-2 grid gap-1 text-sm text-emerald-800 dark:text-emerald-200 sm:grid-cols-2">
              <div>
                <dt className="text-emerald-600 dark:text-emerald-400">Filename</dt>
                <dd>{result.filename}</dd>
              </div>
              <div>
                <dt className="text-emerald-600 dark:text-emerald-400">Status</dt>
                <dd className="capitalize">{result.status}</dd>
              </div>
              <div>
                <dt className="text-emerald-600 dark:text-emerald-400">Chunks</dt>
                <dd>{result.chunk_count}</dd>
              </div>
              <div>
                <dt className="text-emerald-600 dark:text-emerald-400">Uploaded</dt>
                <dd>{formatDate(result.created_at)}</dd>
              </div>
            </dl>
            <button
              type="button"
              onClick={() => navigate(`/documents/${result.id}`)}
              className="mt-3 text-sm font-medium text-emerald-700 underline dark:text-emerald-300"
            >
              View document →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

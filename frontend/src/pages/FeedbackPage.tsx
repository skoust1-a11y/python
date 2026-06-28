import { useEffect, useState } from "react";
import { Star, Send, CheckCircle } from "lucide-react";
import { listDocuments, submitFeedback } from "@/api/client";
import type { DocumentSummary, FeedbackDraft } from "@/api/types";
import { Card } from "@/components/Card";
import { getSessionId } from "@/lib/utils";

const STORAGE_KEY = "legaldoc_feedback_drafts";

function loadDrafts(): FeedbackDraft[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as FeedbackDraft[]) : [];
  } catch {
    return [];
  }
}

function saveDrafts(drafts: FeedbackDraft[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(drafts));
}

export function FeedbackPage() {
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [comment, setComment] = useState("");
  const [queryText, setQueryText] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<FeedbackDraft[]>(loadDrafts);

  useEffect(() => {
    listDocuments(0, 100)
      .then((res) => setDocuments(res.items))
      .catch(() => {});
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (rating < 1) {
      setError("Please select a rating");
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccess(false);

    try {
      await submitFeedback({
        rating,
        comment: comment || null,
        query_text: queryText || null,
        document_id: documentId || null,
        session_id: getSessionId(),
      });

      const draft: FeedbackDraft = {
        id: crypto.randomUUID(),
        rating,
        comment,
        query_text: queryText,
        document_id: documentId || null,
        submitted: true,
        submittedAt: new Date().toISOString(),
      };
      const updated = [draft, ...history].slice(0, 20);
      setHistory(updated);
      saveDrafts(updated);

      setSuccess(true);
      setRating(0);
      setComment("");
      setQueryText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit feedback");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Feedback</h2>
        <p className="mt-1 text-slate-500 dark:text-slate-400">
          Rate your experience and help improve retrieval quality
        </p>
      </div>

      <Card title="Submit Feedback">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Rating
            </label>
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(0)}
                  onClick={() => setRating(star)}
                  className="rounded p-1 transition-transform hover:scale-110"
                >
                  <Star
                    className={`h-8 w-8 ${
                      star <= (hoverRating || rating)
                        ? "fill-amber-400 text-amber-400"
                        : "text-slate-300 dark:text-slate-600"
                    }`}
                  />
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Original question (optional)
            </label>
            <input
              type="text"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              placeholder="What question did you ask?"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Related document (optional)
            </label>
            <select
              value={documentId}
              onChange={(e) => setDocumentId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
            >
              <option value="">None</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.title ?? doc.filename}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Comment (optional)
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={4}
              placeholder="What was helpful or missing?"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          )}

          {success && (
            <div className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
              <CheckCircle className="h-4 w-4" />
              Thank you! Your feedback has been submitted.
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            {submitting ? "Submitting..." : "Submit feedback"}
          </button>
        </form>
      </Card>

      {history.length > 0 && (
        <Card title="Recent Submissions (local)">
          <div className="space-y-3">
            {history.map((item) => (
              <div
                key={item.id}
                className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
              >
                <div className="flex items-center gap-2">
                  <div className="flex">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <Star
                        key={s}
                        className={`h-4 w-4 ${
                          s <= item.rating
                            ? "fill-amber-400 text-amber-400"
                            : "text-slate-300"
                        }`}
                      />
                    ))}
                  </div>
                  {item.submittedAt && (
                    <span className="text-xs text-slate-400">
                      {new Date(item.submittedAt).toLocaleString()}
                    </span>
                  )}
                </div>
                {item.query_text && (
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                    Q: {item.query_text}
                  </p>
                )}
                {item.comment && (
                  <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{item.comment}</p>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

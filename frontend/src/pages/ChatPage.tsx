import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Send, Bot, User, ChevronDown, ChevronUp } from "lucide-react";
import { listDocuments, queryDocuments } from "@/api/client";
import type { ChatMessage, DocumentSummary } from "@/api/types";
import { Card } from "@/components/Card";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { QueryResultPanel } from "@/components/QueryResultPanel";
import { ConfidenceScore } from "@/components/ConfidenceScore";
import { RouteBadge } from "@/components/RouteBadge";
import { SourcesList } from "@/components/SourcesList";

export function ChatPage() {
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentId, setDocumentId] = useState<string>(searchParams.get("doc") ?? "");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listDocuments(0, 100)
      .then((res) => setDocuments(res.items))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const doc = searchParams.get("doc");
    if (doc) setDocumentId(doc);
  }, [searchParams]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = async () => {
    const question = input.trim();
    if (!question || loading) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const response = await queryDocuments({
        question,
        document_id: documentId || null,
      });
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.answer,
        response,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setExpandedId(assistantMsg.id);
    } catch (e) {
      const errMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: e instanceof Error ? e.message : "Query failed. Please try again.",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col gap-4 lg:h-[calc(100vh-6rem)]">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Chat</h2>
          <p className="mt-1 text-slate-500 dark:text-slate-400">
            Ask questions about your legal documents
          </p>
        </div>
        <div className="w-full sm:w-auto">
          <label className="mb-1 block text-xs font-medium text-slate-500">
            Scope to document (optional)
          </label>
          <select
            value={documentId}
            onChange={(e) => setDocumentId(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 sm:min-w-[240px]"
          >
            <option value="">All documents</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.title ?? doc.filename}
              </option>
            ))}
          </select>
        </div>
      </div>

      <Card className="flex flex-1 flex-col overflow-hidden !p-0">
        <div className="flex-1 overflow-y-auto p-4 lg:p-6">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <Bot className="h-12 w-12 text-slate-300" />
              <p className="mt-4 text-slate-500">Start a conversation about your legal documents.</p>
              <p className="mt-1 text-sm text-slate-400">
                Answers include sources, confidence scores, and routing details.
              </p>
            </div>
          )}

          <div className="space-y-6">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}>
                {msg.role === "assistant" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100 dark:bg-brand-900/40">
                    <Bot className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                  </div>
                )}
                <div className={`max-w-[85%] space-y-2 ${msg.role === "user" ? "order-first" : ""}`}>
                  <div
                    className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "bg-brand-600 text-white"
                        : "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200"
                    }`}
                  >
                    {msg.content}
                  </div>

                  {msg.response && (
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900">
                        <ConfidenceScore score={msg.response.confidence_score} size="sm" />
                        <RouteBadge routing={msg.response.routing} />
                      </div>

                      <button
                        type="button"
                        onClick={() => setExpandedId(expandedId === msg.id ? null : msg.id)}
                        className="flex items-center gap-1 text-xs font-medium text-brand-600 hover:underline dark:text-brand-400"
                      >
                        {expandedId === msg.id ? (
                          <>
                            <ChevronUp className="h-3 w-3" /> Hide details
                          </>
                        ) : (
                          <>
                            <ChevronDown className="h-3 w-3" /> Show chunks & sources (
                            {msg.response.sources.length})
                          </>
                        )}
                      </button>

                      {expandedId === msg.id && (
                        <div className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
                          <QueryResultPanel response={msg.response} />
                        </div>
                      )}

                      {!expandedId && msg.response.sources.length > 0 && (
                        <SourcesList sources={msg.response.sources.slice(0, 2)} compact />
                      )}
                    </div>
                  )}
                </div>
                {msg.role === "user" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200 dark:bg-slate-700">
                    <User className="h-4 w-4 text-slate-600 dark:text-slate-300" />
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 dark:bg-brand-900/40">
                  <Bot className="h-4 w-4 text-brand-600" />
                </div>
                <div className="rounded-2xl bg-slate-100 px-4 py-3 dark:bg-slate-800">
                  <LoadingSpinner size="sm" label="Retrieving and synthesizing..." />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        <div className="border-t border-slate-200 p-4 dark:border-slate-800">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage();
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about clauses, contracts, cases..."
              disabled={loading}
              className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              <span className="hidden sm:inline">Send</span>
            </button>
          </form>
        </div>
      </Card>
    </div>
  );
}

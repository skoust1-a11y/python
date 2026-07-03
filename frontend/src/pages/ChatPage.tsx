import { useEffect, useState } from "react";

import { useSearchParams } from "react-router-dom";

import { Bot, FileText } from "lucide-react";

import { listDocuments, queryDocuments } from "@/api/client";

import type { ChatMessage, DocumentSummary } from "@/api/types";

import { AssistantMessage } from "@/components/AssistantMessage";

import { ChatEmptyState } from "@/components/chat/ChatEmptyState";

import { ChatInput } from "@/components/chat/ChatInput";

import { UserMessage } from "@/components/chat/UserMessage";

import { GenerationProgress } from "@/components/GenerationProgress";

import { useAutoScroll } from "@/hooks/useAutoScroll";

import { useGenerationProgress } from "@/hooks/useGenerationProgress";

import { loadStoredResponseMode, storeResponseMode, type ResponseMode } from "@/lib/responseModes";



export function ChatPage() {

  const [searchParams] = useSearchParams();

  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const [input, setInput] = useState("");

  const [loading, setLoading] = useState(false);

  const [documents, setDocuments] = useState<DocumentSummary[]>([]);

  const [documentId, setDocumentId] = useState<string>(searchParams.get("doc") ?? "");

  const [activeMode, setActiveMode] = useState<ResponseMode>(loadStoredResponseMode);

  const [latestAnimatedId, setLatestAnimatedId] = useState<string | null>(null);



  const { steps, currentIndex, complete } = useGenerationProgress(loading);



  const messagesRef = useAutoScroll<HTMLDivElement>({

    dependencies: [messages, loading, currentIndex],

  });



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



  const sendMessage = async (questionOverride?: string) => {

    const question = (questionOverride ?? input).trim();

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



    const startTime = performance.now();



    try {

      const response = await queryDocuments({

        question,

        document_id: documentId || null,

      });

      complete();



      const clientLatencyMs = performance.now() - startTime;

      const assistantId = crypto.randomUUID();

      const assistantMsg: ChatMessage = {

        id: assistantId,

        role: "assistant",

        content: response[activeMode],

        response,

        timestamp: new Date().toISOString(),

        clientLatencyMs,

      };

      setMessages((prev) => [...prev, assistantMsg]);

      setLatestAnimatedId(assistantId);

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



  const selectedDocument = documents.find((d) => d.id === documentId);



  return (

    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">

      <header className="glass-surface shrink-0 border-b px-4 py-3 lg:px-6">

        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">

          <div>

            <h2 className="text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100">

              Legal Document Analysis

            </h2>

            <p className="text-xs text-slate-500 dark:text-slate-400">

              AI-powered retrieval · cited evidence · multi-mode analysis

            </p>

          </div>

          <div className="relative">

            <FileText className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />

            <select

              value={documentId}

              onChange={(e) => setDocumentId(e.target.value)}

              className="focus-ring appearance-none rounded-full border border-slate-200/80 bg-white py-1.5 pl-8 pr-8 text-xs font-medium outline-none transition-colors hover:border-brand-300 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-brand-700"

              title="Scope to document"

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

        {selectedDocument && (

          <p className="mx-auto mt-1 max-w-6xl truncate text-[11px] text-brand-600 dark:text-brand-400">

            Scoped to: {selectedDocument.title ?? selectedDocument.filename}

          </p>

        )}

      </header>



      <div
        ref={messagesRef}
        data-chat-scroll
        className="min-h-0 flex-1 overflow-y-auto scroll-smooth"
      >

        <div className="mx-auto max-w-6xl px-4 py-6 lg:px-6">

          {messages.length === 0 && !loading && (

            <ChatEmptyState onSelectPrompt={sendMessage} />

          )}



          <div className="space-y-10">

            {messages.map((msg) =>

              msg.role === "user" ? (

                <UserMessage key={msg.id} content={msg.content} />

              ) : msg.response ? (

                <AssistantMessage

                  key={msg.id}

                  response={msg.response}

                  activeMode={activeMode}

                  latencyMs={msg.clientLatencyMs}

                  animate={msg.id === latestAnimatedId}

                  onModeChange={handleModeChange}

                  onFollowUp={sendMessage}

                  loading={loading}

                />

              ) : (

                <div key={msg.id} className="animate-slide-up flex items-start gap-3">

                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700">

                    <Bot className="h-4 w-4 text-white" />

                  </div>

                  <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">

                    {msg.content}

                  </div>

                </div>

              ),

            )}



            {loading && (

              <div className="animate-fade-in flex items-start gap-3">

                <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-700 shadow-md shadow-brand-500/20">

                  <Bot className="h-4 w-4 text-white" />

                </div>

                <div className="glass-card w-full max-w-md px-5 py-4">

                  <GenerationProgress steps={steps} currentIndex={currentIndex} />

                </div>

              </div>

            )}

          </div>

        </div>

      </div>



      <ChatInput

        value={input}

        onChange={setInput}

        onSubmit={() => sendMessage()}

        loading={loading}

      />

    </div>

  );

}


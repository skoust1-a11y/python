import { useState } from "react";
import {
  Check,
  Copy,
  Download,
  FileDown,
  FileText,
  MoreHorizontal,
} from "lucide-react";
import type { QueryResponse } from "@/api/types";
import {
  copyToClipboard,
  exportAsMarkdown,
  exportAsPdf,
  exportAsText,
} from "@/lib/exportResponse";
import type { ResponseMode } from "@/lib/responseModes";

interface MessageActionsProps {
  answer: string;
  mode: ResponseMode;
  response: QueryResponse;
}

export function MessageActions({ answer, mode, response }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);

  const handleCopy = async () => {
    await copyToClipboard(answer);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  const handleExport = (type: "pdf" | "markdown" | "text") => {
    setExportOpen(false);
    if (type === "pdf") exportAsPdf(answer, mode, response);
    else if (type === "markdown") exportAsMarkdown(answer, mode, response);
    else exportAsText(answer, mode, response);
  };

  return (
    <div className="flex flex-wrap items-center gap-1">
      <button
        type="button"
        onClick={handleCopy}
        className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
        title="Copy response"
      >
        {copied ? (
          <>
            <Check className="h-3.5 w-3.5 text-emerald-500" />
            Copied
          </>
        ) : (
          <>
            <Copy className="h-3.5 w-3.5" />
            Copy
          </>
        )}
      </button>

      <div className="relative">
        <button
          type="button"
          onClick={() => setExportOpen((prev) => !prev)}
          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          title="Export response"
          aria-expanded={exportOpen}
        >
          <Download className="h-3.5 w-3.5" />
          Export
          <MoreHorizontal className="h-3 w-3 opacity-60" />
        </button>

        {exportOpen && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setExportOpen(false)}
              aria-hidden
            />
            <div className="absolute left-0 top-full z-20 mt-1 min-w-[160px] overflow-hidden rounded-lg border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
              <button
                type="button"
                onClick={() => handleExport("pdf")}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                <FileDown className="h-3.5 w-3.5" />
                PDF
              </button>
              <button
                type="button"
                onClick={() => handleExport("markdown")}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                <FileText className="h-3.5 w-3.5" />
                Markdown
              </button>
              <button
                type="button"
                onClick={() => handleExport("text")}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                <FileText className="h-3.5 w-3.5" />
                Text
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

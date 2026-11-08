import type { QueryResponse } from "@/api/types";
import { RESPONSE_MODE_LABELS, type ResponseMode } from "@/lib/responseModes";
import { countRelevantClauses, countSourceDocuments } from "@/lib/sourceStats";

function formatSourcesMarkdown(response: QueryResponse): string {
  if (response.sources.length === 0) return "_No sources retrieved._\n";

  const lines = response.sources.map((source, index) => {
    const locations = source.locations
      .map((loc) => {
        const parts: string[] = [];
        if (loc.clause_number) parts.push(`Clause ${loc.clause_number}`);
        if (loc.clause_title) parts.push(loc.clause_title);
        if (loc.page_number != null) parts.push(`Page ${loc.page_number}`);
        return parts.join(" · ");
      })
      .filter(Boolean);

    const locationText =
      locations.length > 0 ? `\n  - ${locations.join("\n  - ")}` : "";
    return `${index + 1}. **${source.document_name}**${locationText}`;
  });

  return `${lines.join("\n")}\n`;
}

export function buildMarkdownExport(
  answer: string,
  mode: ResponseMode,
  response: QueryResponse,
): string {
  const docCount = countSourceDocuments(response.sources);
  const clauseCount = countRelevantClauses(response.sources);

  return [
    `# Legal Document Analysis`,
    ``,
    `**Mode:** ${RESPONSE_MODE_LABELS[mode]}`,
    `**Confidence:** ${response.confidence_level} (${Math.round(response.confidence * 100)}%)`,
    `**Generation time:** ${formatLatency(response.latency_ms)}`,
    ``,
    `## Answer`,
    ``,
    answer,
    ``,
    `## Sources`,
    ``,
    `${docCount} Documents · ${clauseCount} Relevant Clauses`,
    ``,
    formatSourcesMarkdown(response),
  ].join("\n");
}

export function buildTextExport(
  answer: string,
  mode: ResponseMode,
  response: QueryResponse,
): string {
  const docCount = countSourceDocuments(response.sources);
  const clauseCount = countRelevantClauses(response.sources);

  const sourceLines = response.sources.map((source, index) => {
    const locations = source.locations
      .map((loc) => {
        const parts: string[] = [];
        if (loc.clause_number) parts.push(`Clause ${loc.clause_number}`);
        if (loc.clause_title) parts.push(loc.clause_title);
        if (loc.page_number != null) parts.push(`Page ${loc.page_number}`);
        return parts.join(" · ");
      })
      .filter(Boolean);
    const locText = locations.length > 0 ? ` (${locations.join("; ")})` : "";
    return `${index + 1}. ${source.document_name}${locText}`;
  });

  return [
    "LEGAL DOCUMENT ANALYSIS",
    "=====================",
    "",
    `Mode: ${RESPONSE_MODE_LABELS[mode]}`,
    `Confidence: ${response.confidence_level} (${Math.round(response.confidence * 100)}%)`,
    `Generation time: ${formatLatency(response.latency_ms)}`,
    "",
    "ANSWER",
    "------",
    "",
    answer,
    "",
    "SOURCES",
    "-------",
    `${docCount} Documents · ${clauseCount} Relevant Clauses`,
    "",
    ...sourceLines,
  ].join("\n");
}

export function formatLatency(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export async function copyToClipboard(text: string): Promise<void> {
  await navigator.clipboard.writeText(text);
}

export function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function exportAsMarkdown(
  answer: string,
  mode: ResponseMode,
  response: QueryResponse,
): void {
  const content = buildMarkdownExport(answer, mode, response);
  downloadFile(content, "legal-response.md", "text/markdown;charset=utf-8");
}

export function exportAsText(
  answer: string,
  mode: ResponseMode,
  response: QueryResponse,
): void {
  const content = buildTextExport(answer, mode, response);
  downloadFile(content, "legal-response.txt", "text/plain;charset=utf-8");
}

export function exportAsPdf(
  answer: string,
  mode: ResponseMode,
  response: QueryResponse,
): void {
  const docCount = countSourceDocuments(response.sources);
  const clauseCount = countRelevantClauses(response.sources);
  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Legal Response</title>
  <style>
    body { font-family: Georgia, "Times New Roman", serif; max-width: 720px; margin: 40px auto; color: #1e293b; line-height: 1.6; }
    h1 { font-size: 22px; margin-bottom: 8px; }
    .meta { font-size: 13px; color: #64748b; margin-bottom: 24px; }
    .badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
    .badge-high { background: #d1fae5; color: #065f46; }
    .badge-medium { background: #fef3c7; color: #92400e; }
    .badge-low { background: #fee2e2; color: #991b1b; }
    .answer { white-space: pre-wrap; font-size: 14px; margin: 24px 0; }
    h2 { font-size: 16px; margin-top: 32px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; }
    .sources-summary { font-size: 13px; color: #64748b; margin-bottom: 12px; }
    ul { padding-left: 20px; font-size: 13px; }
    li { margin-bottom: 8px; }
    @media print { body { margin: 24px; } }
  </style>
</head>
<body>
  <h1>Legal Document Analysis</h1>
  <div class="meta">
    <strong>${RESPONSE_MODE_LABELS[mode]}</strong> ·
    <span class="badge badge-${response.confidence_level.toLowerCase()}">${response.confidence_level}</span> ·
    ${formatLatency(response.latency_ms)}
  </div>
  <h2>Answer</h2>
  <div class="answer">${escapeHtml(answer)}</div>
  <h2>Sources</h2>
  <p class="sources-summary">${docCount} Documents · ${clauseCount} Relevant Clauses</p>
  <ul>
    ${response.sources
      .map((source) => {
        const locations = source.locations
          .map((loc) => {
            const parts: string[] = [];
            if (loc.clause_number) parts.push(`Clause ${loc.clause_number}`);
            if (loc.clause_title) parts.push(loc.clause_title);
            if (loc.page_number != null) parts.push(`Page ${loc.page_number}`);
            return parts.join(" · ");
          })
          .filter(Boolean);
        const locHtml =
          locations.length > 0
            ? `<br/><span style="color:#64748b;font-size:12px">${locations.join("; ")}</span>`
            : "";
        return `<li><strong>${escapeHtml(source.document_name)}</strong>${locHtml}</li>`;
      })
      .join("")}
  </ul>
</body>
</html>`;

  const printWindow = window.open("", "_blank");
  if (!printWindow) return;
  printWindow.document.write(html);
  printWindow.document.close();
  printWindow.focus();
  printWindow.print();
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

import type { ReactNode } from "react";
import type { SnippetHighlight } from "@/api/types";

const HIGHLIGHT_CLASS =
  "rounded bg-amber-200/80 px-0.5 text-slate-900 dark:bg-amber-500/30 dark:text-slate-100";

interface HighlightedChunkExcerptProps {
  highlights: SnippetHighlight[];
}

/**
 * Render a formatted chunk excerpt with keyword highlights and paragraph breaks.
 * Splits on paragraph boundaries preserved by the backend formatter.
 */
export function HighlightedChunkExcerpt({ highlights }: HighlightedChunkExcerptProps) {
  if (highlights.length === 0) {
    return null;
  }

  const paragraphs: ReactNode[][] = [[]];
  let paragraphIndex = 0;
  let key = 0;

  for (const segment of highlights) {
    const parts = segment.text.split(/(\n\n+)/);
    for (const part of parts) {
      if (/^\n\n+$/.test(part)) {
        paragraphIndex += 1;
        paragraphs[paragraphIndex] = paragraphs[paragraphIndex] ?? [];
        continue;
      }
      if (!part) {
        continue;
      }

      const node = segment.matched ? (
        <mark key={key++} className={HIGHLIGHT_CLASS}>
          {part}
        </mark>
      ) : (
        <span key={key++}>{part}</span>
      );
      paragraphs[paragraphIndex].push(node);
    }
  }

  const nonEmpty = paragraphs.filter((nodes) => nodes.length > 0);

  return (
    <div className="legal-markdown-prose max-w-[68ch]">
      {nonEmpty.map((nodes, index) => (
        <p
          key={index}
          className={`legal-p text-sm leading-relaxed text-slate-700 dark:text-slate-300${
            index > 0 ? "" : ""
          }`}
        >
          {nodes}
        </p>
      ))}
    </div>
  );
}

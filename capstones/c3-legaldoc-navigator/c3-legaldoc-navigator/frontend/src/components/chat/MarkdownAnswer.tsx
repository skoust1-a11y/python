import { useState } from "react";
import { AlertTriangle, Info, Lightbulb } from "lucide-react";
import { TypingText } from "@/components/chat/TypingText";
import { renderRichInline } from "@/components/chat/markdownRichText";

const CALLOUT_MARKER_RE =
  /^\[!(NOTE|TIP|WARNING|IMPORTANT)\]\s*/i;
const CALLOUT_LABEL_RE =
  /^(?:\*\*)?(Note|Tip|Important|Warning|Caution)(?:\*\*)?:\s*/i;
const CALLOUT_WARNING_RE =
  /warning|caution|verify|important|manual verification/i;

type CalloutVariant = "note" | "tip" | "warning" | "important";

interface CalloutConfig {
  variant: CalloutVariant;
  icon: React.ReactNode;
  title: string;
}

function parseCallout(content: string): { config: CalloutConfig; body: string } | null {
  let body = content.trim();
  let variant: CalloutVariant = "note";

  const markerMatch = body.match(CALLOUT_MARKER_RE);
  if (markerMatch) {
    variant = markerMatch[1].toLowerCase() as CalloutVariant;
    body = body.slice(markerMatch[0].length).trim();
  } else {
    const labelMatch = body.match(CALLOUT_LABEL_RE);
    if (labelMatch) {
      const label = labelMatch[1].toLowerCase();
      if (label === "warning" || label === "caution") variant = "warning";
      else if (label === "important") variant = "important";
      else if (label === "tip") variant = "tip";
      body = body.slice(labelMatch[0].length).trim();
    } else if (CALLOUT_WARNING_RE.test(body)) {
      variant = "warning";
    } else {
      return null;
    }
  }

  const titles: Record<CalloutVariant, string> = {
    note: "Note",
    tip: "Tip",
    warning: "Warning",
    important: "Important",
  };

  const icons: Record<CalloutVariant, React.ReactNode> = {
    note: <Info className="h-4 w-4 shrink-0" />,
    tip: <Lightbulb className="h-4 w-4 shrink-0" />,
    warning: <AlertTriangle className="h-4 w-4 shrink-0" />,
    important: <AlertTriangle className="h-4 w-4 shrink-0" />,
  };

  return {
    config: { variant, icon: icons[variant], title: titles[variant] },
    body,
  };
}

function parseTableRow(line: string): string[] {
  return line
    .split("|")
    .map((cell) => cell.trim())
    .filter((cell, i, arr) => !(i === 0 && cell === "") && !(i === arr.length - 1 && cell === ""));
}

function isTableSeparator(line: string): boolean {
  return /^\|?[\s:-]+\|[\s|:-]+\|?$/.test(line.trim());
}

function isHorizontalRule(line: string): boolean {
  return /^(\*{3,}|-{3,}|_{3,})$/.test(line.trim());
}

interface MarkdownAnswerProps {
  text: string;
  animate?: boolean;
  onTypingComplete?: () => void;
}

export function MarkdownAnswer({ text, animate = false, onTypingComplete }: MarkdownAnswerProps) {
  const [hasAnimated, setHasAnimated] = useState(false);
  const shouldType = animate && !hasAnimated;

  if (shouldType) {
    return (
      <TypingText
        text={text}
        enabled
        speedMs={6}
        className="legal-markdown"
        onComplete={() => {
          setHasAnimated(true);
          onTypingComplete?.();
        }}
      />
    );
  }

  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      i++;
      continue;
    }

    // Horizontal rule
    if (isHorizontalRule(trimmed)) {
      elements.push(<hr key={key++} className="legal-hr" />);
      i++;
      continue;
    }

    // Fenced code block
    if (trimmed.startsWith("```")) {
      const language = trimmed.slice(3).trim();
      i++;
      const codeLines: string[] = [];
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      if (i < lines.length) i++;
      elements.push(
        <div key={key++} className="legal-code-block-wrap">
          {language && (
            <div className="legal-code-lang" aria-hidden>
              {language}
            </div>
          )}
          <pre className="legal-code-block">
            <code>{codeLines.join("\n")}</code>
          </pre>
        </div>,
      );
      continue;
    }

    // Blockquote — callout or styled quote
    if (trimmed.startsWith(">")) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ""));
        i++;
      }
      const content = quoteLines.join("\n");
      const callout = parseCallout(content);

      if (callout) {
        const { config, body } = callout;
        elements.push(
          <aside
            key={key++}
            className={`legal-callout legal-callout-${config.variant}`}
            role="note"
          >
            <div className="legal-callout-header">
              {config.icon}
              <span>{config.title}</span>
            </div>
            <div className="legal-callout-body">
              {body.split("\n").map((line, li) =>
                line.trim() ? (
                  <p key={li}>{renderRichInline(line.trim(), `callout-${key}-${li}`)}</p>
                ) : null,
              )}
            </div>
          </aside>,
        );
      } else {
        elements.push(
          <blockquote key={key++} className="legal-blockquote">
            {quoteLines.map((ql, qi) => (
              <p key={qi}>{renderRichInline(ql, `bq-${key}-${qi}`)}</p>
            ))}
          </blockquote>,
        );
      }
      continue;
    }

    // Table
    if (trimmed.includes("|") && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const headers = parseTableRow(trimmed);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().includes("|") && !isTableSeparator(lines[i])) {
        rows.push(parseTableRow(lines[i].trim()));
        i++;
      }
      elements.push(
        <div key={key++} className="legal-table-wrap">
          <table className="legal-table">
            <thead>
              <tr>
                {headers.map((h, hi) => (
                  <th key={hi}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr key={ri}>
                  {row.map((cell, ci) => (
                    <td key={ci}>{renderRichInline(cell, `td-${key}-${ri}-${ci}`)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    // Headings
    if (trimmed.startsWith("#### ")) {
      elements.push(
        <h4 key={key++} className="legal-h4">
          {renderRichInline(trimmed.slice(5), `h4-${key}`)}
        </h4>,
      );
      i++;
      continue;
    }
    if (trimmed.startsWith("### ")) {
      elements.push(
        <h3 key={key++} className="legal-h3">
          {renderRichInline(trimmed.slice(4), `h3-${key}`)}
        </h3>,
      );
      i++;
      continue;
    }
    if (trimmed.startsWith("## ")) {
      elements.push(
        <h2 key={key++} className="legal-h2">
          {renderRichInline(trimmed.slice(3), `h2-${key}`)}
        </h2>,
      );
      i++;
      continue;
    }
    if (trimmed.startsWith("# ")) {
      elements.push(
        <h1 key={key++} className="legal-h1">
          {renderRichInline(trimmed.slice(2), `h1-${key}`)}
        </h1>,
      );
      i++;
      continue;
    }

    // Bullet list
    if (/^[-*+]\s/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*+]\s/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*+]\s/, ""));
        i++;
      }
      elements.push(
        <ul key={key++} className="legal-ul">
          {items.map((item, idx) => (
            <li key={idx}>{renderRichInline(item, `ul-${key}-${idx}`)}</li>
          ))}
        </ul>,
      );
      continue;
    }

    // Numbered list
    if (/^\d+\.\s/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s/, ""));
        i++;
      }
      elements.push(
        <ol key={key++} className="legal-ol">
          {items.map((item, idx) => (
            <li key={idx}>{renderRichInline(item, `ol-${key}-${idx}`)}</li>
          ))}
        </ol>,
      );
      continue;
    }

    // Paragraph
    const paraLines: string[] = [trimmed];
    i++;
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].trim().startsWith("#") &&
      !lines[i].trim().startsWith(">") &&
      !lines[i].trim().startsWith("```") &&
      !/^[-*+]\s/.test(lines[i].trim()) &&
      !/^\d+\.\s/.test(lines[i].trim()) &&
      !isHorizontalRule(lines[i].trim()) &&
      !(lines[i].trim().includes("|") && i + 1 < lines.length && isTableSeparator(lines[i + 1]))
    ) {
      paraLines.push(lines[i].trim());
      i++;
    }
    elements.push(
      <p key={key++} className="legal-p">
        {renderRichInline(paraLines.join(" "), `p-${key}`)}
      </p>,
    );
  }

  return (
    <div className="legal-markdown legal-markdown-prose stagger-children">
      {elements}
    </div>
  );
}

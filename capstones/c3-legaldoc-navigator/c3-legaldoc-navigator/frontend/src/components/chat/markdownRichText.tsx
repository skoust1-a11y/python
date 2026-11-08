import type { ReactNode } from "react";
import { LegalCitationBadge } from "@/components/chat/LegalCitationBadge";

const LEGAL_TERM_PATTERN =
  /\b(shall|must|may not|hereby|indemnif\w*|liabilit\w*|termination|warrant\w*|covenant|jurisdiction|governing law|force majeure|confidential\w*|arbitration|breach|damages|obligation|notice period|intellectual property)\b/gi;

/** Matches backend citation patterns (see guardrails/constants.py). */
export const CITATION_PATTERN =
  /(\[(?:Source|S)\s*\d+\]|\bSource\s+\d+\b|\bSection\s+\d+(?:\.\d+)*\b|\bClause\s+\d+(?:\.\d+)*\b|\bArticle\s+[IVXLC\d]+\b|\bParagraph\s+\d+\b|\bExhibit\s+[A-Z\d]+\b)/gi;

function highlightLegalTerms(text: string, keyPrefix: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  const regex = new RegExp(LEGAL_TERM_PATTERN.source, "gi");
  let match: RegExpExecArray | null;
  let termKey = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push(
      <mark
        key={`${keyPrefix}-term-${termKey++}`}
        className="legal-term-highlight rounded-sm bg-amber-100/90 px-0.5 font-medium text-amber-950 dark:bg-amber-900/35 dark:text-amber-100"
      >
        {match[0]}
      </mark>,
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
}

function renderCitationsAndTerms(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const regex = new RegExp(CITATION_PATTERN.source, "gi");
  let last = 0;
  let match: RegExpExecArray | null;
  let partKey = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) {
      nodes.push(...highlightLegalTerms(text.slice(last, match.index), `${keyPrefix}-${partKey}`));
    }
    const label = match[0];
    const isBracketSource = /^\[(?:Source|S)\s*\d+\]$/i.test(label);
    nodes.push(
      <LegalCitationBadge
        key={`${keyPrefix}-cite-${partKey++}`}
        label={label}
        variant={isBracketSource ? "source" : "reference"}
      />,
    );
    last = match.index + label.length;
  }

  if (last < text.length) {
    nodes.push(...highlightLegalTerms(text.slice(last), `${keyPrefix}-tail`));
  }

  return nodes.length > 0 ? nodes : highlightLegalTerms(text, keyPrefix);
}

export function renderRichInline(text: string, keyPrefix = "inline"): ReactNode[] {
  const nodes: ReactNode[] = [];
  const tokenPattern = /(\*\*[^*]+\*\*|\*[^*]+\*|_[^_]+_|`[^`]+`)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  while ((match = tokenPattern.exec(text)) !== null) {
    if (match.index > last) {
      nodes.push(...renderCitationsAndTerms(text.slice(last, match.index), `${keyPrefix}-${key}`));
    }
    const token = match[0];
    if (token.startsWith("**")) {
      nodes.push(
        <strong key={`${keyPrefix}-${key++}`} className="legal-bold font-bold text-slate-950 dark:text-white">
          {renderCitationsAndTerms(token.slice(2, -2), `${keyPrefix}-b${key}`)}
        </strong>,
      );
    } else if (token.startsWith("*") || token.startsWith("_")) {
      nodes.push(
        <em key={`${keyPrefix}-${key++}`} className="legal-italic italic text-slate-700 dark:text-slate-200">
          {renderCitationsAndTerms(token.slice(1, -1), `${keyPrefix}-i${key}`)}
        </em>,
      );
    } else {
      nodes.push(
        <code key={`${keyPrefix}-${key++}`} className="legal-inline-code">
          {token.slice(1, -1)}
        </code>,
      );
    }
    last = match.index + token.length;
  }

  if (last < text.length) {
    nodes.push(...renderCitationsAndTerms(text.slice(last), `${keyPrefix}-end`));
  }

  return nodes;
}

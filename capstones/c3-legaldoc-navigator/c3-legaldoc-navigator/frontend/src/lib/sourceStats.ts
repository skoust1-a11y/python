import type { CitationLocation, SourceCitation } from "@/api/types";

function locationKey(location: CitationLocation): string {
  return [
    location.clause_number ?? "",
    location.clause_title ?? "",
    location.page_number ?? "",
  ].join("|");
}

export function countSourceDocuments(sources: SourceCitation[]): number {
  const seen = new Set<string>();
  for (const source of sources) {
    const key = source.document_id ?? source.document_name.toLowerCase();
    seen.add(key);
  }
  return seen.size;
}

export function countRelevantClauses(sources: SourceCitation[]): number {
  const seen = new Set<string>();
  for (const source of sources) {
    for (const location of source.locations) {
      const key = `${source.document_id ?? source.document_name}:${locationKey(location)}`;
      if (location.clause_number || location.clause_title || location.page_number != null) {
        seen.add(key);
      }
    }
  }
  return seen.size;
}

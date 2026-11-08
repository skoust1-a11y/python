import type { CitationLocation, DirectEvidenceItem } from "@/api/types";

/** Format pinpoint metadata the same way as Evidence Mode source cards. */
export function formatCitationLocation(location: CitationLocation): string | null {
  const parts: string[] = [];
  if (location.clause_number) {
    parts.push(`Clause ${location.clause_number}`);
  }
  if (location.clause_title) {
    parts.push(location.clause_title);
  }
  if (location.page_number != null) {
    parts.push(`Page ${location.page_number}`);
  }
  return parts.length > 0 ? parts.join(" · ") : null;
}

/** Metadata badge labels for a direct-evidence card. */
export function directEvidenceMetadataBadges(item: DirectEvidenceItem): string[] {
  const badges: string[] = [];
  if (item.metadata.clause_number) {
    badges.push(`Clause ${item.metadata.clause_number}`);
  }
  if (item.metadata.clause_title) {
    badges.push(item.metadata.clause_title);
  }
  if (item.page != null) {
    badges.push(`Page ${item.page}`);
  }
  if (item.chunk != null) {
    badges.push(`Chunk ${item.chunk}`);
  }
  return badges;
}

export interface HealthResponse {
  status: string;
  app_name: string;
  version: string;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  status: string;
  chunk_count: number;
  title: string | null;
  file_type: string;
  created_at: string;
}

export interface DocumentSummary {
  id: string;
  filename: string;
  file_type: string;
  title: string | null;
  status: string;
  chunk_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentSummary[];
  total: number;
  skip: number;
  limit: number;
}

export interface DocumentDetailResponse {
  id: string;
  filename: string;
  file_type: string;
  title: string | null;
  status: string;
  storage_path: string | null;
  content_hash: string | null;
  page_count: number | null;
  contract_id: string | null;
  document_subtype: string | null;
  document_date: string | null;
  parties_involved: string[] | null;
  file_size_bytes: number | null;
  chunk_count: number | null;
  keywords: string[] | null;
  summary: string | null;
  doc_metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface QueryRequest {
  question: string;
  document_id?: string | null;
  top_k?: number | null;
  similarity_threshold?: number | null;
  provider?: string | null;
}

export interface RoutingMetadata {
  route: string;
  reason: string;
  confidence: number;
}

export interface CitationLocation {
  clause_number: string | null;
  clause_title: string | null;
  page_number: number | null;
}

export interface SourceCitation {
  document_id: string | null;
  document_name: string;
  score: number;
  source_types: string[];
  locations: CitationLocation[];
  citation_labels: string[];
  entity_id: string | null;
  entity_type: string | null;
}

export interface StructuredMetadata {
  contracts: Record<string, unknown>[];
  clauses: Record<string, unknown>[];
  cases: Record<string, unknown>[];
  metadata_records: Record<string, unknown>[];
  plan_explanation: string | null;
  total_count: number;
}

export interface RelatedDocument {
  document_id: string | null;
  name: string;
  relevance: number;
}

export interface QueryResponse {
  strict: string;
  explain: string;
  analysis: string;
  confidence: number;
  confidence_level: "High" | "Medium" | "Low";
  verification_notice: string | null;
  sources: SourceCitation[];
  related_documents: RelatedDocument[];
  follow_up_questions: string[];
  latency_ms: number;
}

export interface FeedbackRequest {
  rating: number;
  comment?: string | null;
  query_text?: string | null;
  document_id?: string | null;
  session_id?: string | null;
}

export interface FeedbackResponse {
  id: string;
  rating: number;
  comment: string | null;
  created_at: string;
}

export interface ApiError {
  detail: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: QueryResponse;
  timestamp: string;
  clientLatencyMs?: number;
}

export interface FeedbackDraft {
  id: string;
  rating: number;
  comment: string;
  query_text: string;
  document_id: string | null;
  submitted: boolean;
  submittedAt?: string;
}

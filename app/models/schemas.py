"""Pydantic request/response schemas for API contracts."""

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Standard error payload returned by exception handlers."""

    detail: str


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["healthy"])
    app_name: str
    version: str


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    chunk_count: int
    title: str | None = None
    file_type: str
    created_at: datetime


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    file_type: str
    title: str | None = None
    status: str
    chunk_count: int | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentSummary]
    total: int
    skip: int
    limit: int


class DocumentDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    file_type: str
    title: str | None = None
    status: str
    storage_path: str | None = None
    content_hash: str | None = None
    page_count: int | None = None
    contract_id: str | None = None
    document_subtype: str | None = None
    document_date: date | None = None
    parties_involved: list[str] | None = None
    file_size_bytes: int | None = None
    chunk_count: int | None = None
    keywords: list[str] | None = None
    summary: str | None = None
    doc_metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    document_id: UUID | None = Field(
        default=None,
        description="Optional scope: search only within this document",
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of chunks to retrieve (defaults to server config)",
    )
    similarity_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity for retrieved chunks",
    )
    provider: str | None = Field(
        default=None,
        description="LLM provider override: openai or anthropic",
    )


class RoutingMetadata(BaseModel):
    route: str = Field(..., description="Selected retrieval route: rag, sql, or hybrid")
    reason: str = Field(..., description="Classifier justification for the route")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Routing confidence (0–1)")


class SourceCitation(BaseModel):
    document_id: UUID | None = None
    chunk_index: int | None = None
    excerpt: str
    score: float
    citation_label: str | None = None
    source_type: str = Field(
        default="vector",
        description="Provenance: vector, sql_clause, sql_contract, sql_case, etc.",
    )
    entity_id: UUID | None = None
    entity_type: str | None = None
    metadata: dict[str, Any] | None = None


class StructuredMetadata(BaseModel):
    contracts: list[dict[str, Any]] = Field(default_factory=list)
    clauses: list[dict[str, Any]] = Field(default_factory=list)
    cases: list[dict[str, Any]] = Field(default_factory=list)
    metadata_records: list[dict[str, Any]] = Field(default_factory=list)
    plan_explanation: str | None = None
    total_count: int = 0


class QueryResponse(BaseModel):
    answer: str
    explanation: str = Field(
        ...,
        description="Natural-language summary of routing and retrieval steps",
    )
    sources: list[SourceCitation]
    structured_metadata: StructuredMetadata | None = None
    routing: RoutingMetadata
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Rank-weighted retrieval confidence (0–1)",
    )
    provider: str
    retrieved_count: int
    vector_count: int = 0
    sql_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="User satisfaction rating (1–5)")
    comment: str | None = Field(default=None, max_length=2000)
    query_text: str | None = Field(
        default=None,
        max_length=2000,
        description="Original question that received the answer being rated",
    )
    document_id: UUID | None = Field(
        default=None,
        description="Document context for the rated interaction",
    )
    session_id: UUID | None = Field(
        default=None,
        description="Chat session identifier for correlating feedback",
    )


class FeedbackResponse(BaseModel):
    id: UUID
    rating: int
    comment: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Handoff
# ---------------------------------------------------------------------------


class ConversationTurn(BaseModel):
    role: str = Field(..., description="Message role: user or assistant")
    message: str = Field(..., min_length=1, max_length=8000)


class HandoffRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    answer: str | None = Field(
        default=None,
        max_length=16000,
        description="Assistant response to evaluate for escalation",
    )
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    sources: list[SourceCitation] = Field(default_factory=list)
    conversation_history: list[ConversationTurn] = Field(default_factory=list)
    document_id: UUID | None = Field(
        default=None,
        description="Primary document context for the interaction",
    )
    session_id: UUID | None = Field(
        default=None,
        description="Chat session identifier for correlating conversation history",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Optional user requesting human review",
    )


class RetrievedDocumentSummary(BaseModel):
    id: UUID
    filename: str
    title: str | None = None
    file_type: str
    status: str
    contract_id: str | None = None
    document_subtype: str | None = None


class HandoffResponse(BaseModel):
    escalated: bool
    escalation_id: UUID | None = None
    reasons: list[str] = Field(default_factory=list)
    summary: str | None = None
    conversation_history: list[ConversationTurn] = Field(default_factory=list)
    retrieved_documents: list[RetrievedDocumentSummary] = Field(default_factory=list)
    sources: list[SourceCitation] = Field(default_factory=list)
    status: str | None = None
    created_at: datetime | None = None

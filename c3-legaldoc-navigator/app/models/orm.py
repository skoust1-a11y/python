"""SQLAlchemy ORM models for Legal Document Analysis."""

import uuid
from datetime import date, datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.database.session import Base


class TimestampMixin:
    """Reusable created/updated timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="analyst")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    documents: Mapped[list["Document"]] = relationship(back_populates="user")
    chat_messages: Mapped[list["ChatHistory"]] = relationship(back_populates="user")

    __table_args__ = (
        Index("ix_users_role", "role"),
        Index("ix_users_is_active", "is_active"),
    )


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(1024))
    title: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    content_hash: Mapped[str | None] = mapped_column(String(64))
    page_count: Mapped[int | None] = mapped_column(Integer)
    contract_id: Mapped[str | None] = mapped_column(String(100))
    document_subtype: Mapped[str | None] = mapped_column(String(100))
    document_date: Mapped[date | None] = mapped_column(Date)
    parties_involved: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    chunk_count: Mapped[int | None] = mapped_column(Integer)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    summary: Mapped[str | None] = mapped_column(Text)
    doc_metadata: Mapped[dict | None] = mapped_column(JSONB)

    user: Mapped[Optional["User"]] = relationship(back_populates="documents")
    clauses: Mapped[list["Clause"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    embeddings: Mapped[list["DocumentEmbedding"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="source_document",
        foreign_keys="Citation.source_document_id",
        cascade="all, delete-orphan",
    )
    chat_messages: Mapped[list["ChatHistory"]] = relationship(back_populates="document")

    __table_args__ = (
        Index("ix_documents_user_id", "user_id"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_content_hash", "content_hash"),
        Index("ix_documents_created_at", "created_at"),
        Index("ix_documents_contract_id", "contract_id", unique=True),
        Index("ix_documents_document_subtype", "document_subtype"),
        Index("ix_documents_document_date", "document_date"),
        Index("ix_documents_keywords_gin", "keywords", postgresql_using="gin"),
        Index("ix_documents_parties_gin", "parties_involved", postgresql_using="gin"),
    )


class Clause(Base, TimestampMixin):
    __tablename__ = "clauses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_clause_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clauses.id", ondelete="SET NULL"),
        nullable=True,
    )
    clause_number: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    clause_type: Mapped[str | None] = mapped_column(String(64))
    page_number: Mapped[int | None] = mapped_column(Integer)
    position_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_level: Mapped[str | None] = mapped_column(String(20))
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    related_clause_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    clause_metadata: Mapped[dict | None] = mapped_column(JSONB)

    document: Mapped["Document"] = relationship(back_populates="clauses")
    parent_clause: Mapped[Optional["Clause"]] = relationship(
        remote_side="Clause.id", back_populates="child_clauses"
    )
    child_clauses: Mapped[list["Clause"]] = relationship(back_populates="parent_clause")
    embeddings: Mapped[list["DocumentEmbedding"]] = relationship(back_populates="clause")
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="source_clause",
        foreign_keys="Citation.source_clause_id",
    )

    __table_args__ = (
        CheckConstraint(
            "risk_level IS NULL OR risk_level IN ('Low', 'Medium', 'High', 'Critical')",
            name="ck_clauses_risk_level",
        ),
        Index("ix_clauses_document_id", "document_id"),
        Index("ix_clauses_parent_clause_id", "parent_clause_id"),
        Index("ix_clauses_clause_type", "clause_type"),
        Index("ix_clauses_document_position", "document_id", "position_order"),
        Index("ix_clauses_risk_level", "risk_level"),
        Index("ix_clauses_keywords_gin", "keywords", postgresql_using="gin"),
        Index("ix_clauses_document_risk", "document_id", "risk_level"),
    )


class Case(Base, TimestampMixin):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_citation: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    case_name: Mapped[str] = mapped_column(String(512), nullable=False)
    court: Mapped[str | None] = mapped_column(String(255))
    jurisdiction: Mapped[str | None] = mapped_column(String(128))
    filing_date: Mapped[date | None] = mapped_column(Date)
    decision_date: Mapped[date | None] = mapped_column(Date)
    case_type: Mapped[str | None] = mapped_column(String(100))
    case_status: Mapped[str | None] = mapped_column(String(50))
    primary_judge: Mapped[str | None] = mapped_column(String(200))
    docket_number: Mapped[str | None] = mapped_column(String(128))
    summary: Mapped[str | None] = mapped_column(Text)
    full_text: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    legal_act_references: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.VECTOR_DIMENSION))
    case_metadata: Mapped[dict | None] = mapped_column(JSONB)

    citations: Mapped[list["Citation"]] = relationship(back_populates="cited_case")

    __table_args__ = (
        Index("ix_cases_court", "court"),
        Index("ix_cases_jurisdiction", "jurisdiction"),
        Index("ix_cases_decision_date", "decision_date"),
        Index("ix_cases_docket_number", "docket_number"),
        Index("ix_cases_filing_date", "filing_date"),
        Index("ix_cases_case_type", "case_type"),
        Index("ix_cases_case_status", "case_status"),
        Index("ix_cases_keywords_gin", "keywords", postgresql_using="gin"),
        Index("ix_cases_legal_act_refs_gin", "legal_act_references", postgresql_using="gin"),
        Index(
            "ix_cases_embedding_ivfflat",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class Statute(Base, TimestampMixin):
    __tablename__ = "statutes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    statute_code: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    act_name: Mapped[str | None] = mapped_column(Text)
    act_short_name: Mapped[str | None] = mapped_column(String(200))
    title: Mapped[str | None] = mapped_column(String(512))
    section_title: Mapped[str | None] = mapped_column(Text)
    jurisdiction: Mapped[str | None] = mapped_column(String(128))
    enactment_year: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str | None] = mapped_column(String(100))
    section_number: Mapped[str | None] = mapped_column(String(64))
    full_text: Mapped[str | None] = mapped_column(Text)
    application_notes: Mapped[str | None] = mapped_column(Text)
    effective_date: Mapped[date | None] = mapped_column(Date)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.VECTOR_DIMENSION))
    statute_metadata: Mapped[dict | None] = mapped_column(JSONB)

    citations: Mapped[list["Citation"]] = relationship(back_populates="cited_statute")

    __table_args__ = (
        Index("ix_statutes_jurisdiction", "jurisdiction"),
        Index("ix_statutes_section_number", "section_number"),
        Index("ix_statutes_effective_date", "effective_date"),
        Index("ix_statutes_act_short_name", "act_short_name"),
        Index("ix_statutes_category", "category"),
        Index("ix_statutes_enactment_year", "enactment_year"),
        Index("ix_statutes_keywords_gin", "keywords", postgresql_using="gin"),
        Index(
            "ix_statutes_embedding_ivfflat",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class Citation(Base, TimestampMixin):
    """Links source content (documents/clauses) to cited cases or statutes."""

    __tablename__ = "citations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,
    )
    source_clause_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clauses.id", ondelete="CASCADE"),
        nullable=True,
    )
    cited_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    cited_statute_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("statutes.id", ondelete="SET NULL"),
        nullable=True,
    )
    citation_text: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(Text)
    position_start: Mapped[int | None] = mapped_column(Integer)
    position_end: Mapped[int | None] = mapped_column(Integer)

    source_document: Mapped[Optional["Document"]] = relationship(
        back_populates="citations", foreign_keys=[source_document_id]
    )
    source_clause: Mapped[Optional["Clause"]] = relationship(
        back_populates="citations", foreign_keys=[source_clause_id]
    )
    cited_case: Mapped[Optional["Case"]] = relationship(back_populates="citations")
    cited_statute: Mapped[Optional["Statute"]] = relationship(back_populates="citations")

    __table_args__ = (
        Index("ix_citations_source_type", "source_type"),
        Index("ix_citations_source_document_id", "source_document_id"),
        Index("ix_citations_source_clause_id", "source_clause_id"),
        Index("ix_citations_cited_case_id", "cited_case_id"),
        Index("ix_citations_cited_statute_id", "cited_statute_id"),
    )


class DocumentEmbedding(Base, TimestampMixin):
    """Chunk-level embeddings stored inline with pgvector."""

    __tablename__ = "document_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    clause_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clauses.id", ondelete="SET NULL"),
        nullable=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    vector_store_id: Mapped[str | None] = mapped_column(String(255))
    token_count: Mapped[int | None] = mapped_column(Integer)
    chunk_text: Mapped[str | None] = mapped_column(Text)
    content_preview: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.VECTOR_DIMENSION))
    embed_metadata: Mapped[dict | None] = mapped_column(JSONB)

    document: Mapped["Document"] = relationship(back_populates="embeddings")
    clause: Mapped[Optional["Clause"]] = relationship(back_populates="embeddings")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_embeddings_doc_chunk"),
        Index("ix_document_embeddings_document_id", "document_id"),
        Index("ix_document_embeddings_clause_id", "clause_id"),
        Index("ix_document_embeddings_embedding_model", "embedding_model"),
        Index("ix_document_embeddings_keywords_gin", "keywords", postgresql_using="gin"),
        Index(
            "ix_document_embeddings_embedding_ivfflat",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class Feedback(Base, TimestampMixin):
    """User feedback on query quality and usefulness."""

    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    query_text: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    document: Mapped[Optional["Document"]] = relationship()

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_feedback_rating"),
        Index("ix_feedback_document_id", "document_id"),
        Index("ix_feedback_created_at", "created_at"),
    )


class HandoffEscalation(Base, TimestampMixin):
    """Human handoff escalation record for low-confidence or high-risk queries."""

    __tablename__ = "handoff_escalations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    conversation_history: Mapped[list | None] = mapped_column(JSONB)
    retrieved_documents: Mapped[list | None] = mapped_column(JSONB)
    sources: Mapped[list | None] = mapped_column(JSONB)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    escalation_reasons: Mapped[list] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    user: Mapped[Optional["User"]] = relationship()
    document: Mapped[Optional["Document"]] = relationship()

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'assigned', 'resolved')",
            name="ck_handoff_escalations_status",
        ),
        Index("ix_handoff_escalations_session_id", "session_id"),
        Index("ix_handoff_escalations_status", "status"),
        Index("ix_handoff_escalations_created_at", "created_at"),
    )


class ChatHistory(Base, TimestampMixin):
    __tablename__ = "chat_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, default=uuid.uuid4
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(128))
    token_count: Mapped[int | None] = mapped_column(Integer)
    chat_metadata: Mapped[dict | None] = mapped_column(JSONB)

    user: Mapped[Optional["User"]] = relationship(back_populates="chat_messages")
    document: Mapped[Optional["Document"]] = relationship(back_populates="chat_messages")

    __table_args__ = (
        Index("ix_chat_history_user_id", "user_id"),
        Index("ix_chat_history_document_id", "document_id"),
        Index("ix_chat_history_session_id", "session_id"),
        Index("ix_chat_history_created_at", "created_at"),
        Index("ix_chat_history_session_created", "session_id", "created_at"),
    )

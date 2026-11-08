"""Initial legal document analysis schema.

Revision ID: 001_initial_legal_schema
Revises:
Create Date: 2026-06-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_legal_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TIMESTAMP_TABLES = (
    "users",
    "documents",
    "clauses",
    "cases",
    "statutes",
    "citations",
    "document_embeddings",
    "chat_history",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="analyst"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_is_active", "users", ["is_active"])

    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_citation", sa.String(length=512), nullable=False),
        sa.Column("case_name", sa.String(length=512), nullable=False),
        sa.Column("court", sa.String(length=255), nullable=True),
        sa.Column("jurisdiction", sa.String(length=128), nullable=True),
        sa.Column("decision_date", sa.Date(), nullable=True),
        sa.Column("docket_number", sa.String(length=128), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("case_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_citation"),
    )
    op.create_index("ix_cases_court", "cases", ["court"])
    op.create_index("ix_cases_jurisdiction", "cases", ["jurisdiction"])
    op.create_index("ix_cases_decision_date", "cases", ["decision_date"])
    op.create_index("ix_cases_docket_number", "cases", ["docket_number"])

    op.create_table(
        "statutes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("statute_code", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("jurisdiction", sa.String(length=128), nullable=True),
        sa.Column("section_number", sa.String(length=64), nullable=True),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("statute_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("statute_code"),
    )
    op.create_index("ix_statutes_jurisdiction", "statutes", ["jurisdiction"])
    op.create_index("ix_statutes_section_number", "statutes", ["section_number"])
    op.create_index("ix_statutes_effective_date", "statutes", ["effective_date"])

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("file_type", sa.String(length=32), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("doc_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])

    op.create_table(
        "clauses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_clause_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("clause_number", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("clause_type", sa.String(length=64), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("position_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clause_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_clause_id"], ["clauses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clauses_document_id", "clauses", ["document_id"])
    op.create_index("ix_clauses_parent_clause_id", "clauses", ["parent_clause_id"])
    op.create_index("ix_clauses_clause_type", "clauses", ["clause_type"])
    op.create_index("ix_clauses_document_position", "clauses", ["document_id", "position_order"])

    op.create_table(
        "citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_clause_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cited_case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cited_statute_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("citation_text", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("position_start", sa.Integer(), nullable=True),
        sa.Column("position_end", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["cited_case_id"], ["cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cited_statute_id"], ["statutes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_clause_id"], ["clauses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_citations_source_type", "citations", ["source_type"])
    op.create_index("ix_citations_source_document_id", "citations", ["source_document_id"])
    op.create_index("ix_citations_source_clause_id", "citations", ["source_clause_id"])
    op.create_index("ix_citations_cited_case_id", "citations", ["cited_case_id"])
    op.create_index("ix_citations_cited_statute_id", "citations", ["cited_statute_id"])

    op.create_table(
        "document_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clause_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding_model", sa.String(length=128), nullable=False),
        sa.Column("vector_store_id", sa.String(length=255), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("content_preview", sa.Text(), nullable=True),
        sa.Column("embed_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clause_id"], ["clauses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_embeddings_doc_chunk"),
    )
    op.create_index("ix_document_embeddings_document_id", "document_embeddings", ["document_id"])
    op.create_index("ix_document_embeddings_clause_id", "document_embeddings", ["clause_id"])
    op.create_index(
        "ix_document_embeddings_embedding_model", "document_embeddings", ["embedding_model"]
    )

    op.create_table(
        "chat_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("chat_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_history_user_id", "chat_history", ["user_id"])
    op.create_index("ix_chat_history_document_id", "chat_history", ["document_id"])
    op.create_index("ix_chat_history_session_id", "chat_history", ["session_id"])
    op.create_index("ix_chat_history_created_at", "chat_history", ["created_at"])
    op.create_index("ix_chat_history_session_created", "chat_history", ["session_id", "created_at"])

    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in TIMESTAMP_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
            """
        )


def downgrade() -> None:
    for table in reversed(TIMESTAMP_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    op.drop_index("ix_chat_history_session_created", table_name="chat_history")
    op.drop_index("ix_chat_history_created_at", table_name="chat_history")
    op.drop_index("ix_chat_history_session_id", table_name="chat_history")
    op.drop_index("ix_chat_history_document_id", table_name="chat_history")
    op.drop_index("ix_chat_history_user_id", table_name="chat_history")
    op.drop_table("chat_history")

    op.drop_index("ix_document_embeddings_embedding_model", table_name="document_embeddings")
    op.drop_index("ix_document_embeddings_clause_id", table_name="document_embeddings")
    op.drop_index("ix_document_embeddings_document_id", table_name="document_embeddings")
    op.drop_table("document_embeddings")

    op.drop_index("ix_citations_cited_statute_id", table_name="citations")
    op.drop_index("ix_citations_cited_case_id", table_name="citations")
    op.drop_index("ix_citations_source_clause_id", table_name="citations")
    op.drop_index("ix_citations_source_document_id", table_name="citations")
    op.drop_index("ix_citations_source_type", table_name="citations")
    op.drop_table("citations")

    op.drop_index("ix_clauses_document_position", table_name="clauses")
    op.drop_index("ix_clauses_clause_type", table_name="clauses")
    op.drop_index("ix_clauses_parent_clause_id", table_name="clauses")
    op.drop_index("ix_clauses_document_id", table_name="clauses")
    op.drop_table("clauses")

    op.drop_index("ix_documents_created_at", table_name="documents")
    op.drop_index("ix_documents_content_hash", table_name="documents")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_user_id", table_name="documents")
    op.drop_table("documents")

    op.drop_index("ix_statutes_effective_date", table_name="statutes")
    op.drop_index("ix_statutes_section_number", table_name="statutes")
    op.drop_index("ix_statutes_jurisdiction", table_name="statutes")
    op.drop_table("statutes")

    op.drop_index("ix_cases_docket_number", table_name="cases")
    op.drop_index("ix_cases_decision_date", table_name="cases")
    op.drop_index("ix_cases_jurisdiction", table_name="cases")
    op.drop_index("ix_cases_court", table_name="cases")
    op.drop_table("cases")

    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_table("users")

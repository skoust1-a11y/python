"""Enhance schema with legal RAG features from reference design.

Revision ID: 002_enhance_legal_rag_features
Revises: 001_initial_legal_schema
Create Date: 2026-06-28

Adds keyword arrays, risk scoring, case/statute enrichment columns,
pgvector embedding columns, and GIN/IVFFLAT indexes for hybrid retrieval.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "002_enhance_legal_rag_features"
down_revision: Union[str, None] = "001_initial_legal_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VECTOR_DIM = 1536


def upgrade() -> None:
    # --- documents (maps reference: document_metadata) ---
    op.add_column("documents", sa.Column("contract_id", sa.String(length=100), nullable=True))
    op.add_column("documents", sa.Column("document_subtype", sa.String(length=100), nullable=True))
    op.add_column("documents", sa.Column("document_date", sa.Date(), nullable=True))
    op.add_column(
        "documents",
        sa.Column("parties_involved", postgresql.ARRAY(sa.Text()), nullable=True),
    )
    op.add_column("documents", sa.Column("file_size_bytes", sa.BigInteger(), nullable=True))
    op.add_column("documents", sa.Column("chunk_count", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("keywords", postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column("documents", sa.Column("summary", sa.Text(), nullable=True))

    op.create_index("ix_documents_contract_id", "documents", ["contract_id"], unique=True)
    op.create_index("ix_documents_document_subtype", "documents", ["document_subtype"])
    op.create_index("ix_documents_document_date", "documents", ["document_date"])
    op.execute(
        "CREATE INDEX ix_documents_keywords_gin ON documents USING gin (keywords)"
    )
    op.execute(
        "CREATE INDEX ix_documents_parties_gin ON documents USING gin (parties_involved)"
    )

    # --- clauses (maps reference: contract_clause_index) ---
    op.add_column("clauses", sa.Column("risk_level", sa.String(length=20), nullable=True))
    op.add_column("clauses", sa.Column("keywords", postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column(
        "clauses",
        sa.Column(
            "related_clause_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_clauses_risk_level",
        "clauses",
        "risk_level IS NULL OR risk_level IN ('Low', 'Medium', 'High', 'Critical')",
    )
    op.create_index("ix_clauses_risk_level", "clauses", ["risk_level"])
    op.create_index("ix_clauses_document_risk", "clauses", ["document_id", "risk_level"])
    op.execute("CREATE INDEX ix_clauses_keywords_gin ON clauses USING gin (keywords)")

    # --- cases (maps reference: case_law_metadata) ---
    op.add_column("cases", sa.Column("filing_date", sa.Date(), nullable=True))
    op.add_column("cases", sa.Column("case_type", sa.String(length=100), nullable=True))
    op.add_column("cases", sa.Column("case_status", sa.String(length=50), nullable=True))
    op.add_column("cases", sa.Column("primary_judge", sa.String(length=200), nullable=True))
    op.add_column("cases", sa.Column("keywords", postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column(
        "cases",
        sa.Column("legal_act_references", postgresql.ARRAY(sa.Text()), nullable=True),
    )
    op.add_column("cases", sa.Column("embedding", Vector(VECTOR_DIM), nullable=True))

    op.create_index("ix_cases_filing_date", "cases", ["filing_date"])
    op.create_index("ix_cases_case_type", "cases", ["case_type"])
    op.create_index("ix_cases_case_status", "cases", ["case_status"])
    op.execute("CREATE INDEX ix_cases_keywords_gin ON cases USING gin (keywords)")
    op.execute(
        "CREATE INDEX ix_cases_legal_act_refs_gin ON cases USING gin (legal_act_references)"
    )
    op.execute(
        """
        CREATE INDEX ix_cases_embedding_ivfflat ON cases
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
        """
    )

    # --- statutes (maps reference: legal_acts_reference) ---
    op.add_column("statutes", sa.Column("act_name", sa.Text(), nullable=True))
    op.add_column("statutes", sa.Column("act_short_name", sa.String(length=200), nullable=True))
    op.add_column("statutes", sa.Column("section_title", sa.Text(), nullable=True))
    op.add_column("statutes", sa.Column("enactment_year", sa.Integer(), nullable=True))
    op.add_column("statutes", sa.Column("category", sa.String(length=100), nullable=True))
    op.add_column("statutes", sa.Column("application_notes", sa.Text(), nullable=True))
    op.add_column("statutes", sa.Column("keywords", postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column("statutes", sa.Column("embedding", Vector(VECTOR_DIM), nullable=True))

    op.create_index("ix_statutes_act_short_name", "statutes", ["act_short_name"])
    op.create_index("ix_statutes_category", "statutes", ["category"])
    op.create_index("ix_statutes_enactment_year", "statutes", ["enactment_year"])
    op.execute("CREATE INDEX ix_statutes_keywords_gin ON statutes USING gin (keywords)")
    op.execute(
        """
        CREATE INDEX ix_statutes_embedding_ivfflat ON statutes
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
        """
    )

    # --- document_embeddings: inline vectors for hybrid chunk search ---
    op.add_column("document_embeddings", sa.Column("keywords", postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column("document_embeddings", sa.Column("embedding", Vector(VECTOR_DIM), nullable=True))
    op.execute(
        "CREATE INDEX ix_document_embeddings_keywords_gin ON document_embeddings USING gin (keywords)"
    )
    op.execute(
        """
        CREATE INDEX ix_document_embeddings_embedding_ivfflat ON document_embeddings
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_embeddings_embedding_ivfflat")
    op.execute("DROP INDEX IF EXISTS ix_document_embeddings_keywords_gin")
    op.drop_column("document_embeddings", "embedding")
    op.drop_column("document_embeddings", "keywords")

    op.execute("DROP INDEX IF EXISTS ix_statutes_embedding_ivfflat")
    op.execute("DROP INDEX IF EXISTS ix_statutes_keywords_gin")
    op.drop_index("ix_statutes_enactment_year", table_name="statutes")
    op.drop_index("ix_statutes_category", table_name="statutes")
    op.drop_index("ix_statutes_act_short_name", table_name="statutes")
    op.drop_column("statutes", "embedding")
    op.drop_column("statutes", "keywords")
    op.drop_column("statutes", "application_notes")
    op.drop_column("statutes", "category")
    op.drop_column("statutes", "enactment_year")
    op.drop_column("statutes", "section_title")
    op.drop_column("statutes", "act_short_name")
    op.drop_column("statutes", "act_name")

    op.execute("DROP INDEX IF EXISTS ix_cases_embedding_ivfflat")
    op.execute("DROP INDEX IF EXISTS ix_cases_legal_act_refs_gin")
    op.execute("DROP INDEX IF EXISTS ix_cases_keywords_gin")
    op.drop_index("ix_cases_case_status", table_name="cases")
    op.drop_index("ix_cases_case_type", table_name="cases")
    op.drop_index("ix_cases_filing_date", table_name="cases")
    op.drop_column("cases", "embedding")
    op.drop_column("cases", "legal_act_references")
    op.drop_column("cases", "keywords")
    op.drop_column("cases", "primary_judge")
    op.drop_column("cases", "case_status")
    op.drop_column("cases", "case_type")
    op.drop_column("cases", "filing_date")

    op.execute("DROP INDEX IF EXISTS ix_clauses_keywords_gin")
    op.drop_index("ix_clauses_document_risk", table_name="clauses")
    op.drop_index("ix_clauses_risk_level", table_name="clauses")
    op.drop_constraint("ck_clauses_risk_level", "clauses", type_="check")
    op.drop_column("clauses", "related_clause_ids")
    op.drop_column("clauses", "keywords")
    op.drop_column("clauses", "risk_level")

    op.execute("DROP INDEX IF EXISTS ix_documents_parties_gin")
    op.execute("DROP INDEX IF EXISTS ix_documents_keywords_gin")
    op.drop_index("ix_documents_document_date", table_name="documents")
    op.drop_index("ix_documents_document_subtype", table_name="documents")
    op.drop_index("ix_documents_contract_id", table_name="documents")
    op.drop_column("documents", "summary")
    op.drop_column("documents", "keywords")
    op.drop_column("documents", "chunk_count")
    op.drop_column("documents", "file_size_bytes")
    op.drop_column("documents", "parties_involved")
    op.drop_column("documents", "document_date")
    op.drop_column("documents", "document_subtype")
    op.drop_column("documents", "contract_id")

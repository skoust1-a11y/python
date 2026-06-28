"""Add handoff_escalations table for human review workflow.

Revision ID: 005_add_handoff_escalations_table
Revises: 004_add_feedback_table
Create Date: 2026-06-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_add_handoff_escalations_table"
down_revision: Union[str, None] = "004_add_feedback_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "handoff_escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("conversation_history", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("retrieved_documents", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("escalation_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
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
        sa.CheckConstraint(
            "status IN ('pending', 'assigned', 'resolved')",
            name="ck_handoff_escalations_status",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_handoff_escalations_session_id",
        "handoff_escalations",
        ["session_id"],
    )
    op.create_index(
        "ix_handoff_escalations_status",
        "handoff_escalations",
        ["status"],
    )
    op.create_index(
        "ix_handoff_escalations_created_at",
        "handoff_escalations",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_handoff_escalations_created_at", table_name="handoff_escalations")
    op.drop_index("ix_handoff_escalations_status", table_name="handoff_escalations")
    op.drop_index("ix_handoff_escalations_session_id", table_name="handoff_escalations")
    op.drop_table("handoff_escalations")

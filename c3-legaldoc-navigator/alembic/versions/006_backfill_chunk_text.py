"""Backfill chunk_text from content_preview for legacy embedding rows.

Revision ID: 006_backfill_chunk_text
Revises: 005_handoff_escalations
Create Date: 2026-07-06
"""

from typing import Sequence, Union

from alembic import op

revision: str = "006_backfill_chunk_text"
down_revision: Union[str, None] = "005_handoff_escalations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE document_embeddings
        SET chunk_text = content_preview
        WHERE (chunk_text IS NULL OR chunk_text = '')
          AND content_preview IS NOT NULL
          AND content_preview != ''
        """
    )


def downgrade() -> None:
    pass

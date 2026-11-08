"""Add chunk_text column to document_embeddings.

Revision ID: 003_add_chunk_text_column
Revises: 002_enhance_legal_rag_features
Create Date: 2026-06-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_add_chunk_text_column"
down_revision: Union[str, None] = "002_enhance_legal_rag_features"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("document_embeddings", sa.Column("chunk_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_embeddings", "chunk_text")

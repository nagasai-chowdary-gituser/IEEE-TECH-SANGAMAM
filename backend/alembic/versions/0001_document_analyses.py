"""create document_analyses

Revision ID: 0001_document_analyses
Revises:
Create Date: 2026-08-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_document_analyses"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "document_analyses" in inspector.get_table_names():
        return
    op.create_table(
        "document_analyses",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=True),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("file_type", sa.String(length=16), nullable=True),
        sa.Column("document_type", sa.String(length=32), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata_result_json", sa.Text(), nullable=True),
        sa.Column("preprocessing_result_json", sa.Text(), nullable=True),
        sa.Column("final_score", sa.Integer(), nullable=True),
        sa.Column("final_status", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("document_analyses")

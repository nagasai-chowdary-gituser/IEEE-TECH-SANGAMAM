"""add explanation cache and pipeline stage

Revision ID: 0005_productization
Revises: 0004_evidence_fusion
Create Date: 2026-08-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_productization"
down_revision: Union[str, None] = "0004_evidence_fusion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("document_analyses")}
    with op.batch_alter_table("document_analyses") as batch:
        if "pipeline_stage" not in columns:
            batch.add_column(sa.Column("pipeline_stage", sa.String(length=64), nullable=True))
        if "ai_explanation_json" not in columns:
            batch.add_column(sa.Column("ai_explanation_json", sa.Text(), nullable=True))
        if "ai_explanation_created_at" not in columns:
            batch.add_column(sa.Column("ai_explanation_created_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("document_analyses")}
    with op.batch_alter_table("document_analyses") as batch:
        for name in ("ai_explanation_created_at", "ai_explanation_json", "pipeline_stage"):
            if name in columns:
                batch.drop_column(name)

"""add document intelligence result column

Revision ID: 0003_document_intelligence
Revises: 0002_visual_forensics
Create Date: 2026-08-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_document_intelligence"
down_revision: Union[str, None] = "0002_visual_forensics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("document_analyses")}
    with op.batch_alter_table("document_analyses") as batch:
        if "document_intelligence_result_json" not in columns:
            batch.add_column(sa.Column("document_intelligence_result_json", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("document_analyses")}
    with op.batch_alter_table("document_analyses") as batch:
        if "document_intelligence_result_json" in columns:
            batch.drop_column("document_intelligence_result_json")

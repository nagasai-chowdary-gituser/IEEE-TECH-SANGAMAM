"""add visual forensics result columns

Revision ID: 0002_visual_forensics
Revises: 0001_document_analyses
Create Date: 2026-08-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_visual_forensics"
down_revision: Union[str, None] = "0001_document_analyses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("document_analyses")}
    with op.batch_alter_table("document_analyses") as batch:
        if "ela_result_json" not in columns:
            batch.add_column(sa.Column("ela_result_json", sa.Text(), nullable=True))
        if "copy_move_result_json" not in columns:
            batch.add_column(sa.Column("copy_move_result_json", sa.Text(), nullable=True))
        if "visual_forensics_result_json" not in columns:
            batch.add_column(sa.Column("visual_forensics_result_json", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("document_analyses")}
    with op.batch_alter_table("document_analyses") as batch:
        if "visual_forensics_result_json" in columns:
            batch.drop_column("visual_forensics_result_json")
        if "copy_move_result_json" in columns:
            batch.drop_column("copy_move_result_json")
        if "ela_result_json" in columns:
            batch.drop_column("ela_result_json")

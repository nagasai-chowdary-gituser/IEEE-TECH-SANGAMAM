"""add evidence fusion columns

Revision ID: 0004_evidence_fusion
Revises: 0003_document_intelligence
Create Date: 2026-08-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_evidence_fusion"
down_revision: Union[str, None] = "0003_document_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("document_analyses")}
    with op.batch_alter_table("document_analyses") as batch:
        if "fusion_result_json" not in columns:
            batch.add_column(sa.Column("fusion_result_json", sa.Text(), nullable=True))
        if "overall_risk_score" not in columns:
            batch.add_column(sa.Column("overall_risk_score", sa.Integer(), nullable=True))
        if "risk_level" not in columns:
            batch.add_column(sa.Column("risk_level", sa.String(length=32), nullable=True))
        if "assessment_confidence" not in columns:
            batch.add_column(sa.Column("assessment_confidence", sa.Float(), nullable=True))
        if "analysis_coverage" not in columns:
            batch.add_column(sa.Column("analysis_coverage", sa.Float(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("document_analyses")}
    with op.batch_alter_table("document_analyses") as batch:
        for name in (
            "analysis_coverage",
            "assessment_confidence",
            "risk_level",
            "overall_risk_score",
            "fusion_result_json",
        ):
            if name in columns:
                batch.drop_column(name)

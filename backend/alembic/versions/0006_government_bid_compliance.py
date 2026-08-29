"""create compliance_analyses

Revision ID: 0006_government_bid_compliance
Revises: 0005_productization
Create Date: 2026-08-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_government_bid_compliance"
down_revision: Union[str, None] = "0005_productization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "compliance_analyses" in inspector.get_table_names():
        return
    op.create_table(
        "compliance_analyses",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("forensic_analysis_id", sa.String(length=36), nullable=True),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("pipeline_stage", sa.String(length=64), nullable=True),
        sa.Column("extracted_fields_json", sa.Text(), nullable=True),
        sa.Column("pan_result_json", sa.Text(), nullable=True),
        sa.Column("gst_result_json", sa.Text(), nullable=True),
        sa.Column("integrity_result_json", sa.Text(), nullable=True),
        sa.Column("aggregation_json", sa.Text(), nullable=True),
        sa.Column("overall_status", sa.String(length=32), nullable=True),
        sa.Column("compliance_risk_score", sa.Integer(), nullable=True),
        sa.Column("enterprise_name", sa.String(length=512), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_compliance_analyses_forensic_analysis_id", "compliance_analyses", ["forensic_analysis_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "compliance_analyses" in inspector.get_table_names():
        op.drop_index("ix_compliance_analyses_forensic_analysis_id", table_name="compliance_analyses")
        op.drop_table("compliance_analyses")

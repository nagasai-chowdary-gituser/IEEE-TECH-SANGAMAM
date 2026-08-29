"""create reference signatures and signature comparisons

Revision ID: 0007_signature_verification
Revises: 0006_government_bid_compliance
Create Date: 2026-08-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_signature_verification"
down_revision: Union[str, None] = "0006_government_bid_compliance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "reference_signatures" not in tables:
        op.create_table(
            "reference_signatures",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("label", sa.String(length=128), nullable=True),
            sa.Column("original_filename", sa.String(length=512), nullable=False),
            sa.Column("stored_filename", sa.String(length=255), nullable=False),
            sa.Column("file_path", sa.String(length=1024), nullable=False),
            sa.Column("file_type", sa.String(length=16), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("sha256", sa.String(length=64), nullable=False),
            sa.Column("width", sa.Integer(), nullable=True),
            sa.Column("height", sa.Integer(), nullable=True),
            sa.Column("ink_ratio", sa.Float(), nullable=True),
            sa.Column("quality_score", sa.Float(), nullable=True),
            sa.Column("preprocessing_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    if "signature_comparisons" not in tables:
        op.create_table(
            "signature_comparisons",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("reference_id", sa.String(length=36), nullable=False),
            sa.Column("forensic_analysis_id", sa.String(length=36), nullable=True),
            sa.Column("original_filename", sa.String(length=512), nullable=False),
            sa.Column("stored_filename", sa.String(length=255), nullable=True),
            sa.Column("file_path", sa.String(length=1024), nullable=True),
            sa.Column("file_type", sa.String(length=16), nullable=True),
            sa.Column("file_size", sa.Integer(), nullable=True),
            sa.Column("sha256", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("pipeline_stage", sa.String(length=64), nullable=True),
            sa.Column("candidates_json", sa.Text(), nullable=True),
            sa.Column("selected_region_json", sa.Text(), nullable=True),
            sa.Column("document_quality_json", sa.Text(), nullable=True),
            sa.Column("comparison_json", sa.Text(), nullable=True),
            sa.Column("fusion_json", sa.Text(), nullable=True),
            sa.Column("tamper_json", sa.Text(), nullable=True),
            sa.Column("combined_json", sa.Text(), nullable=True),
            sa.Column("overall_status", sa.String(length=64), nullable=True),
            sa.Column("page_preview_artifact", sa.String(length=128), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_signature_comparisons_reference_id", "signature_comparisons", ["reference_id"])
        op.create_index("ix_signature_comparisons_forensic_analysis_id", "signature_comparisons", ["forensic_analysis_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "signature_comparisons" in inspector.get_table_names():
        op.drop_index("ix_signature_comparisons_forensic_analysis_id", table_name="signature_comparisons")
        op.drop_index("ix_signature_comparisons_reference_id", table_name="signature_comparisons")
        op.drop_table("signature_comparisons")
    if "reference_signatures" in inspector.get_table_names():
        op.drop_table("reference_signatures")

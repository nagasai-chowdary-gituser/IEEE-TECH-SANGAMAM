"""AI usage events and temporary abuse blocks

Revision ID: 0009_ai_usage
Revises: 0008_certificate_analyzer
Create Date: 2026-08-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_ai_usage"
down_revision: Union[str, None] = "0008_certificate_analyzer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=False),
        sa.Column("endpoint", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("cached", sa.Boolean(), nullable=False),
        sa.Column("rate_limited", sa.Boolean(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False),
        sa.Column("error_class", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_ai_usage_events_subject", "ai_usage_events", ["subject"])
    op.create_index("ix_ai_usage_events_ip", "ai_usage_events", ["ip"])
    op.create_table(
        "ai_abuse_blocks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("reason", sa.String(length=128), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ai_abuse_blocks_subject", "ai_abuse_blocks", ["subject"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_ai_abuse_blocks_subject", table_name="ai_abuse_blocks")
    op.drop_table("ai_abuse_blocks")
    op.drop_index("ix_ai_usage_events_ip", table_name="ai_usage_events")
    op.drop_index("ix_ai_usage_events_subject", table_name="ai_usage_events")
    op.drop_table("ai_usage_events")

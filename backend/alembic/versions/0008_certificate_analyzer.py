"""nullable reference_id for certificate analyzer without comparison

Revision ID: 0008_certificate_analyzer
Revises: 0007_signature_verification
Create Date: 2026-08-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_certificate_analyzer"
down_revision: Union[str, None] = "0007_signature_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "signature_comparisons" not in inspector.get_table_names():
        return
    info = bind.exec_driver_sql("PRAGMA table_info(signature_comparisons)").fetchall()
    reference = next((row for row in info if row[1] == "reference_id"), None)
    if reference is None or int(reference[3]) == 0:
        return
    col_defs = []
    col_names = []
    for _cid, name, coltype, notnull, default, pk in info:
        col_names.append(name)
        pieces = [f'"{name}"', coltype or "TEXT"]
        if pk:
            pieces.append("PRIMARY KEY")
        elif name != "reference_id" and int(notnull) == 1:
            pieces.append("NOT NULL")
        if default is not None:
            pieces.append(f"DEFAULT {default}")
        col_defs.append(" ".join(pieces))
    quoted = ", ".join(f'"{name}"' for name in col_names)
    bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
    bind.exec_driver_sql(f"CREATE TABLE signature_comparisons_new ({', '.join(col_defs)})")
    bind.exec_driver_sql(f"INSERT INTO signature_comparisons_new ({quoted}) SELECT {quoted} FROM signature_comparisons")
    bind.exec_driver_sql("DROP TABLE signature_comparisons")
    bind.exec_driver_sql("ALTER TABLE signature_comparisons_new RENAME TO signature_comparisons")
    bind.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_signature_comparisons_reference_id ON signature_comparisons (reference_id)"
    )
    bind.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_signature_comparisons_forensic_analysis_id ON signature_comparisons (forensic_analysis_id)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "signature_comparisons" not in inspector.get_table_names():
        return
    with op.batch_alter_table("signature_comparisons") as batch:
        batch.alter_column("reference_id", existing_type=sa.String(length=36), nullable=False)

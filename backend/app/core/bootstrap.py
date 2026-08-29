from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.logging import get_logger

logger = get_logger(__name__)


def ensure_storage_directories() -> None:
    settings = get_settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.processed_path.mkdir(parents=True, exist_ok=True)


def init_database() -> None:
    """Create tables if they do not exist. Alembic remains the source of schema evolution."""
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()
    _ensure_signature_reference_nullable()
    logger.info("database_initialized")


def _ensure_sqlite_columns() -> None:
    if not str(engine.url).startswith("sqlite"):
        return
    needed = (
        "ela_result_json",
        "copy_move_result_json",
        "visual_forensics_result_json",
        "document_intelligence_result_json",
        "fusion_result_json",
        "overall_risk_score",
        "risk_level",
        "assessment_confidence",
        "analysis_coverage",
        "pipeline_stage",
        "ai_explanation_json",
        "ai_explanation_created_at",
    )
    with engine.begin() as connection:
        existing = {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(document_analyses)").fetchall()
        }
        column_sql = {
            "ela_result_json": "TEXT",
            "copy_move_result_json": "TEXT",
            "visual_forensics_result_json": "TEXT",
            "document_intelligence_result_json": "TEXT",
            "fusion_result_json": "TEXT",
            "overall_risk_score": "INTEGER",
            "risk_level": "VARCHAR(32)",
            "assessment_confidence": "FLOAT",
            "analysis_coverage": "FLOAT",
            "pipeline_stage": "VARCHAR(64)",
            "ai_explanation_json": "TEXT",
            "ai_explanation_created_at": "DATETIME",
        }
        for column in needed:
            if column not in existing:
                connection.exec_driver_sql(
                    f"ALTER TABLE document_analyses ADD COLUMN {column} {column_sql[column]}"
                )
                logger.info("added_sqlite_column column=%s", column)


def _ensure_signature_reference_nullable() -> None:
    """Existing local DBs still have NOT NULL reference_id from 0007. Certificate Analyzer allows none."""
    if not str(engine.url).startswith("sqlite"):
        return
    with engine.begin() as connection:
        tables = {
            row[0]
            for row in connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "signature_comparisons" not in tables:
            return
        info = connection.exec_driver_sql("PRAGMA table_info(signature_comparisons)").fetchall()
        reference = next((row for row in info if row[1] == "reference_id"), None)
        if reference is None or int(reference[3]) == 0:
            return
        col_defs: list[str] = []
        col_names: list[str] = []
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
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.exec_driver_sql(f"CREATE TABLE signature_comparisons_new ({', '.join(col_defs)})")
        connection.exec_driver_sql(
            f"INSERT INTO signature_comparisons_new ({quoted}) SELECT {quoted} FROM signature_comparisons"
        )
        connection.exec_driver_sql("DROP TABLE signature_comparisons")
        connection.exec_driver_sql("ALTER TABLE signature_comparisons_new RENAME TO signature_comparisons")
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_signature_comparisons_reference_id ON signature_comparisons (reference_id)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_signature_comparisons_forensic_analysis_id ON signature_comparisons (forensic_analysis_id)"
        )
        logger.info("sqlite_signature_reference_id_made_nullable")

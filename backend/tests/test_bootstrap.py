from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import bootstrap, database
from app.core.database import Base
from app.models.compliance import ComplianceAnalysis
from app.models.document_analysis import AnalysisStatus, DocumentAnalysis
from app.models.signature import SignatureComparison


def test_recover_interrupted_runs_fails_stale_records_once(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'recover.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    monkeypatch.setattr(bootstrap, "_interrupted_runs_recovered", False)

    with session_factory() as db:
        db.add_all(
            [
                DocumentAnalysis(id="doc-stale", original_filename="a.pdf", status=AnalysisStatus.PROCESSING),
                DocumentAnalysis(id="doc-done", original_filename="b.pdf", status=AnalysisStatus.COMPLETE),
                ComplianceAnalysis(id="comp-stale", original_filename="c.pdf", status="PROCESSING"),
                SignatureComparison(id="sig-stale", original_filename="e.png", status="PENDING"),
                SignatureComparison(id="sig-waiting", original_filename="f.png", status="NEEDS_REGION"),
            ]
        )
        db.commit()

    bootstrap.recover_interrupted_runs()

    with session_factory() as db:
        assert db.get(DocumentAnalysis, "doc-stale").status == AnalysisStatus.FAILED
        assert db.get(DocumentAnalysis, "doc-stale").error_message
        assert db.get(DocumentAnalysis, "doc-done").status == AnalysisStatus.COMPLETE
        assert db.get(ComplianceAnalysis, "comp-stale").status == "FAILED"
        assert db.get(SignatureComparison, "sig-stale").status == "FAILED"
        assert db.get(SignatureComparison, "sig-waiting").status == "NEEDS_REGION"

        db.add(DocumentAnalysis(id="doc-new", original_filename="d.pdf", status=AnalysisStatus.PROCESSING))
        db.commit()

    bootstrap.recover_interrupted_runs()

    with session_factory() as db:
        assert db.get(DocumentAnalysis, "doc-new").status == AnalysisStatus.PROCESSING

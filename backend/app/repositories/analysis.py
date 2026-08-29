from sqlalchemy import desc, func, select

from app.models.document_analysis import AnalysisStatus, DocumentAnalysis
from sqlalchemy.orm import Session


class AnalysisRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, original_filename: str) -> DocumentAnalysis:
        record = DocumentAnalysis(
            original_filename=original_filename,
            status=AnalysisStatus.PENDING,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get(self, analysis_id: str) -> DocumentAnalysis | None:
        return self.db.get(DocumentAnalysis, analysis_id)

    def save(self, record: DocumentAnalysis) -> DocumentAnalysis:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_analyses(self, *, limit: int, offset: int) -> tuple[list[DocumentAnalysis], int]:
        total = self.db.scalar(select(func.count()).select_from(DocumentAnalysis)) or 0
        items = list(
            self.db.scalars(
                select(DocumentAnalysis)
                .order_by(desc(DocumentAnalysis.created_at), desc(DocumentAnalysis.id))
                .offset(offset)
                .limit(limit)
            ).all()
        )
        return items, int(total)

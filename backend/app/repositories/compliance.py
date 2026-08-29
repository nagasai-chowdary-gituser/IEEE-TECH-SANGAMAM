from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.compliance import ComplianceAnalysis, ComplianceStatus


class ComplianceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, original_filename: str, forensic_analysis_id: str | None) -> ComplianceAnalysis:
        record = ComplianceAnalysis(
            original_filename=original_filename,
            forensic_analysis_id=forensic_analysis_id,
            status=ComplianceStatus.PENDING.value,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get(self, compliance_id: str) -> ComplianceAnalysis | None:
        return self.db.get(ComplianceAnalysis, compliance_id)

    def save(self, record: ComplianceAnalysis) -> ComplianceAnalysis:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_analyses(self, *, limit: int, offset: int) -> tuple[list[ComplianceAnalysis], int]:
        total = self.db.scalar(select(func.count()).select_from(ComplianceAnalysis)) or 0
        items = list(
            self.db.scalars(
                select(ComplianceAnalysis)
                .order_by(desc(ComplianceAnalysis.created_at), desc(ComplianceAnalysis.id))
                .offset(offset)
                .limit(limit)
            ).all()
        )
        return items, int(total)

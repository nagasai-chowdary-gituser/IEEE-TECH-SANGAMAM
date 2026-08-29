from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.signature import ReferenceSignature, SignatureComparison


class SignatureRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_reference(self, record: ReferenceSignature) -> ReferenceSignature:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_reference(self, reference_id: str) -> ReferenceSignature | None:
        return self.db.get(ReferenceSignature, reference_id)

    def list_references(self) -> list[ReferenceSignature]:
        return list(self.db.scalars(select(ReferenceSignature).order_by(desc(ReferenceSignature.created_at))).all())

    def delete_reference(self, record: ReferenceSignature) -> None:
        self.db.delete(record)
        self.db.commit()

    def create_comparison(self, record: SignatureComparison) -> SignatureComparison:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_comparison(self, comparison_id: str) -> SignatureComparison | None:
        return self.db.get(SignatureComparison, comparison_id)

    def save_comparison(self, record: SignatureComparison) -> SignatureComparison:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_comparisons(self, *, limit: int, offset: int) -> tuple[list[SignatureComparison], int]:
        total = self.db.scalar(select(func.count()).select_from(SignatureComparison)) or 0
        items = list(
            self.db.scalars(
                select(SignatureComparison)
                .order_by(desc(SignatureComparison.created_at), desc(SignatureComparison.id))
                .offset(offset)
                .limit(limit)
            ).all()
        )
        return items, int(total)

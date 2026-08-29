"""Map OCR/intelligence fields onto certificate labels without inventing values."""

from __future__ import annotations

from app.schemas.intelligence import DocumentIntelligenceResult
from app.schemas.signature import CertificateField

FIELD_LABELS = {
    "name": "Student name",
    "document_number": "Certificate / registration number",
    "issue_date": "Issue date",
    "expiry_date": "Valid until",
    "date_of_birth": "Date of birth",
    "institution": "Institution",
    "degree": "Degree / course",
    "registration_number": "Registration number",
    "issuing_authority": "Issuing authority",
    "marks": "Marks / grades",
}


def certificate_fields(intelligence: DocumentIntelligenceResult | None) -> list[CertificateField]:
    if intelligence is None:
        return []
    out: list[CertificateField] = []
    seen: set[tuple[str, str]] = set()
    for item in intelligence.fields:
        key = (item.field_type, item.value.strip())
        if not item.value.strip() or key in seen:
            continue
        seen.add(key)
        out.append(
            CertificateField(
                field_id=item.field_id,
                label=FIELD_LABELS.get(item.field_type, item.field_type.replace("_", " ").title()),
                value=item.value.strip(),
                confidence=item.confidence,
                source=str(item.source),
            )
        )
    return out[:24]

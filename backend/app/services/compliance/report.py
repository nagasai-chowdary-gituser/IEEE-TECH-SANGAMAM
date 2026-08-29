from __future__ import annotations

import textwrap

import fitz

from app.models.compliance import ComplianceAnalysis
from app.models.document_analysis import DocumentAnalysis
from app.schemas.compliance import CertificateFields, ComplianceAggregation, IdentifierVerification, IntegrityAssessment
from app.utils.serializers import shorten_sha256

DISCLAIMER = (
    "This Government Bid Compliance report is a decision-support assessment based on "
    "configured identifier verification services and digital forensic analysis of the "
    "uploaded certificate. It is not legal proof, government approval, or signer identity verification."
)


def build_compliance_report(record: ComplianceAnalysis, forensic: DocumentAnalysis | None) -> bytes:
    fields = CertificateFields.model_validate_json(record.extracted_fields_json) if record.extracted_fields_json else None
    pan = IdentifierVerification.model_validate_json(record.pan_result_json) if record.pan_result_json else None
    gst = IdentifierVerification.model_validate_json(record.gst_result_json) if record.gst_result_json else None
    integrity = IntegrityAssessment.model_validate_json(record.integrity_result_json) if record.integrity_result_json else None
    aggregation = ComplianceAggregation.model_validate_json(record.aggregation_json) if record.aggregation_json else None

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    y = 52
    margin = 48

    def line(text: str, *, size: float = 9.5, bold: bool = False) -> None:
        nonlocal y, page
        font = "hebo" if bold else "helv"
        for wrapped in textwrap.wrap(text or "—", width=96) or ["—"]:
            if y > 780:
                page = doc.new_page(width=595, height=842)
                y = 52
            page.insert_text((margin, y), wrapped, fontsize=size, fontname=font, color=(0.14, 0.12, 0.10))
            y += 13
        y += 4

    def head(text: str) -> None:
        nonlocal y
        y += 8
        line(text, size=12, bold=True)

    line("DocuVerify Government Bid Compliance", size=16, bold=True)
    line("Forensic risk assessment based on available digital evidence.", size=9)
    head("Certificate identification")
    line(f"Filename: {record.original_filename}")
    line(f"Compliance ID: {record.id}")
    line(f"Created: {record.created_at.isoformat() if record.created_at else '—'}")
    if forensic and forensic.sha256:
        line(f"Fingerprint: {shorten_sha256(forensic.sha256)} (SHA-256)")
    head("Extracted certificate details")
    if fields:
        line(f"Enterprise name: {fields.enterprise_name or 'not extracted'}")
        line(f"Udyam number: {fields.udyam_number or 'not extracted'}")
        line(f"Registration date: {fields.registration_date or 'not extracted'}")
    head("PAN extraction and verification")
    _ident_lines(line, pan, "PAN")
    head("GSTIN extraction and verification")
    _ident_lines(line, gst, "GSTIN")
    head("Certificate forensic integrity")
    if integrity:
        line(f"Integrity level: {integrity.level}")
        line(f"Forensic risk level: {integrity.forensic_risk_level or '—'}")
        line(f"Coverage: {integrity.analysis_coverage if integrity.analysis_coverage is not None else '—'}")
        line(integrity.summary)
        for finding in integrity.top_findings:
            line(f"- {finding}")
        for note in integrity.limitations[:8]:
            line(f"Limitation: {note}")
    else:
        line("Integrity assessment unavailable.")
    head("Final compliance assessment")
    if aggregation:
        line(f"Status: {aggregation.overall_status}")
        line(f"Compliance concern score: {aggregation.compliance_risk_score} (0 = no concern, 100 = highest concern)")
        line(aggregation.assessment_summary)
        line(f"Recommended action: {aggregation.recommended_action}")
    head("Disclaimer")
    line(DISCLAIMER)

    count = doc.page_count
    for index, item in enumerate(doc, start=1):
        item.insert_text(
            (48, 820),
            f"DocuVerify Government Bid Compliance · page {index} of {count}",
            fontsize=8,
            fontname="helv",
            color=(0.45, 0.42, 0.38),
        )
    extracted = "".join(item.get_text() for item in doc).lower()
    for phrase in ("legally verified", "forgery confirmed", "100% genuine", "definitely fake", "government-approved"):
        if phrase in extracted:
            doc.close()
            raise RuntimeError("Compliance report contained forbidden language.")
    data = doc.tobytes()
    doc.close()
    return data


def _ident_lines(line, item: IdentifierVerification | None, label: str) -> None:
    if item is None:
        line(f"{label}: not evaluated")
        return
    line(f"Extracted {label}: {item.extracted_value or 'not extracted'}")
    line(f"Format validation: {item.format_status}")
    line(f"Verification outcome: {item.outcome}")
    if item.verified_at:
        line(f"Verified at: {item.verified_at.isoformat()}")
    if item.details:
        for key, value in list(item.details.items())[:6]:
            line(f"{key}: {value}")
    if item.limitation:
        line(item.limitation)

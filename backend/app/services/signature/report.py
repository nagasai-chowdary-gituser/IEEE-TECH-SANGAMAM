from __future__ import annotations

import json
import textwrap

import fitz

from app.models.signature import ReferenceSignature, SignatureComparison
from app.schemas.signature import CertificateIntegrityAssessment, CombinedSignatureAssessment, SignatureFusion
from app.utils.serializers import shorten_sha256

DISCLAIMER = (
    "This certificate analysis reports technical evidence from completed forensic, OCR, signature-integrity, "
    "and optional reference-comparison layers. It does not independently establish legal authenticity, "
    "legal forgery, or signer identity."
)

ACTIONS = {
    "CERTIFICATE_CLEAR": (
        "No significant manipulation evidence was detected in the completed analysis. "
        "This result does not independently establish legal authenticity."
    ),
    "REVIEW_REQUIRED": (
        "Manual review is recommended because suspicious evidence was detected but was not sufficient "
        "for a strong technical conclusion."
    ),
    "ELEVATED_CONCERN": "Multiple forensic inconsistencies were detected. Verification against an authoritative source is recommended.",
    "HIGH_MANIPULATION_CONCERN": (
        "Strong or corroborating forensic manipulation indicators were detected. "
        "The document should not be treated as verified without manual or authoritative review."
    ),
    "INCONCLUSIVE": "Reliable assessment was limited by image quality or incomplete analysis coverage.",
}


def build_signature_report(record: SignatureComparison, reference: ReferenceSignature | None) -> bytes:
    certificate = None
    combined = None
    if record.combined_json:
        raw = json.loads(record.combined_json)
        if isinstance(raw, dict) and "document_content" in raw:
            certificate = CertificateIntegrityAssessment.model_validate(raw)
        else:
            combined = CombinedSignatureAssessment.model_validate(raw)
    fusion = SignatureFusion.model_validate_json(record.fusion_json) if record.fusion_json else None
    tamper = json.loads(record.tamper_json) if record.tamper_json else None

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

    line("DocuVerify Certificate Analysis Report", size=16, bold=True)
    line("Full-certificate forensic analysis with independent signature and optional reference streams.", size=9)
    head("Analysis identification")
    line(f"Analysis ID: {record.id}")
    line(f"Created: {record.created_at.isoformat() if record.created_at else '—'}")
    head("Document information")
    line(f"Filename: {record.original_filename}")
    if record.sha256:
        line(f"Fingerprint: {shorten_sha256(record.sha256)}")
    if certificate:
        head("Overall Certificate Integrity Assessment")
        line(f"Status: {certificate.overall_status}")
        line(f"Confidence: {int(round(certificate.confidence * 100))}%")
        line(f"Analysis coverage: {int(round(certificate.analysis_coverage * 100))}%")
        line(certificate.summary)
        line(certificate.recommended_action or ACTIONS.get(certificate.overall_status, ""))
        head("Full-document forensic findings")
        line(f"Status: {certificate.document_content.status}")
        line(certificate.document_content.summary)
        for item in certificate.document_content.findings:
            line(f"Finding: {item}")
        head("Suspicious text/content findings")
        text_findings = [item for item in certificate.overlay_regions if item.kind in {"text", "copy_move", "suspicious"}]
        if text_findings:
            for item in text_findings[:8]:
                line(f"{item.label}: {item.explanation}")
        else:
            line("No localized suspicious text or copy-move boxes were emitted by completed checks.")
        for field in certificate.extracted_fields[:12]:
            line(f"Extracted field {field.label}: {field.value}")
        head("Signature integrity findings")
        line(f"Status: {certificate.signature_integrity.status}")
        line(certificate.signature_integrity.summary)
        for item in certificate.signature_integrity.findings:
            line(f"Finding: {item}")
        head("Reference signature comparison")
        if certificate.reference_comparison:
            line(f"Status: {certificate.reference_comparison.status}")
            line(certificate.reference_comparison.summary)
            line(f"Reference: {(reference.label if reference else None) or 'unlabeled'}")
        else:
            line("Reference comparison was not requested.")
        head("Completed checks")
        line(", ".join(certificate.completed_checks) or "—")
        head("Unavailable checks")
        line(", ".join(certificate.unavailable_checks) or "None recorded")
        head("Technical limitations")
        for item in certificate.limitations:
            line(item)
        head("Recommended action")
        line(certificate.recommended_action)
        head("Visual evidence references")
        line("Page preview, signature crop, and overlay artifacts are stored with this analysis when generated.")
    else:
        head("Legacy comparison assessment")
        if fusion:
            line(f"Reference comparison: {fusion.overall_status}")
            line(fusion.assessment_summary)
        if combined:
            line(combined.summary)
        if tamper:
            line(f"Tamper level: {tamper.get('level')}")
    line(DISCLAIMER, size=8)
    data = doc.tobytes()
    doc.close()
    return data

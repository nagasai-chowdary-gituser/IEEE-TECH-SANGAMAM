from __future__ import annotations

import textwrap

import fitz
from fastapi import HTTPException

from app.core.config import Settings
from app.models.document_analysis import DocumentAnalysis
from app.services.forensics.artifacts import resolve_artifact_path
from app.utils.serializers import (
    public_copy_move,
    public_ela,
    public_fusion,
    public_intelligence,
    public_metadata,
    public_preprocessing,
)

DISCLAIMER = (
    "Forensic risk assessment based on available digital evidence. "
    "This report is not legal proof of forgery or authenticity and does not "
    "verify signer identity or external registry records."
)

FORBIDDEN = (
    "confirmed fake",
    "legally verified",
    "authentic guarantee",
    "forgery confirmed",
    "100% authentic",
    "document is fake",
)


class _Pager:
    def __init__(self) -> None:
        self.doc = fitz.open()
        self.page = self.doc.new_page(width=595, height=842)
        self.y = 52
        self.margin = 48

    def _newline(self) -> None:
        if self.y > 780:
            self.page = self.doc.new_page(width=595, height=842)
            self.y = 52

    def heading(self, text: str, size: float = 16) -> None:
        self._newline()
        self.page.insert_text((self.margin, self.y), text, fontsize=size, fontname="helv", color=(0.12, 0.10, 0.08))
        self.y += size + 8

    def subhead(self, text: str) -> None:
        self.y += 6
        self._newline()
        self.page.insert_text((self.margin, self.y), text, fontsize=11.5, fontname="hebo", color=(0.12, 0.10, 0.08))
        self.y += 16

    def body(self, text: str, *, muted: bool = False) -> None:
        color = (0.38, 0.35, 0.32) if muted else (0.16, 0.14, 0.12)
        for line in textwrap.wrap(text.strip() or "—", width=96) or ["—"]:
            self._newline()
            self.page.insert_text((self.margin, self.y), line, fontsize=9.5, fontname="helv", color=color)
            self.y += 13
        self.y += 3

    def image(self, path: str, caption: str) -> None:
        if self.y > 580:
            self.page = self.doc.new_page(width=595, height=842)
            self.y = 52
        try:
            rect = fitz.Rect(self.margin, self.y, self.margin + 320, self.y + 170)
            self.page.insert_image(rect, filename=path, keep_proportion=True)
            self.y += 176
            self.body(caption, muted=True)
        except Exception:
            self.body("Evidence image could not be embedded. The file was not available.", muted=True)


def build_report_pdf(record: DocumentAnalysis, settings: Settings) -> bytes:
    fusion = public_fusion(record.fusion_result_json)
    metadata = public_metadata(record.metadata_result_json)
    ela = public_ela(record.ela_result_json)
    copy_move = public_copy_move(record.copy_move_result_json)
    intelligence = public_intelligence(record.document_intelligence_result_json)
    preprocessing = public_preprocessing(record.preprocessing_result_json)

    pager = _Pager()
    pager.heading("DocuVerify", 18)
    pager.body("Forensic analysis report", muted=True)
    pager.subhead("Document identification")
    pager.body(f"Filename: {record.original_filename}")
    pager.body(f"Document type: {record.document_type or '—'}")
    pager.body(f"File type: {record.file_type or '—'}")
    pager.body(f"Pages: {preprocessing.page_count if preprocessing else '—'}")
    pager.body(f"Analysis ID: {record.id}")
    pager.body(f"Created: {record.created_at.isoformat() if record.created_at else '—'}")
    if record.sha256:
        pager.body(f"Fingerprint: {record.sha256[:12]}…{record.sha256[-8:]} (SHA-256)")
    else:
        pager.body("Fingerprint: unavailable")

    pager.subhead("Final risk assessment")
    if fusion:
        pager.body(f"Risk level: {fusion.risk_level}")
        pager.body(f"Overall risk score: {fusion.overall_risk_score}")
        pager.body(f"Assessment confidence: {fusion.assessment_confidence:.2f}")
        pager.body(f"Analysis coverage: {fusion.analysis_coverage:.2f}")
        pager.body(f"Recommended action: {fusion.recommended_action}")
        pager.body(fusion.assessment_summary)
        pager.body(fusion.corroboration.description)
    else:
        pager.body("A fused risk assessment is not available for this analysis.")

    pager.subhead("Top findings")
    if fusion and fusion.top_findings:
        for item in fusion.top_findings:
            pager.body(f"{item.rank}. [{item.layer}] {item.finding} (severity {item.severity})")
    else:
        pager.body("No ranked findings were recorded.")

    pager.subhead("Metadata findings")
    if metadata:
        pager.body(metadata.summary)
        for signal in metadata.signals[:8]:
            pager.body(f"- {signal.finding} ({signal.severity})")
    else:
        pager.body("Metadata analysis was not available.")

    pager.subhead("Visual forensic findings")
    if ela:
        pager.body(f"ELA: {ela.summary} (score {ela.suspicion_score}, quality {ela.analysis_quality})")
    else:
        pager.body("ELA was not available.")
    if copy_move:
        pager.body(f"Copy-move: {copy_move.summary} (score {copy_move.suspicion_score})")
    else:
        pager.body("Copy-move analysis was not available.")

    pager.subhead("Document intelligence findings")
    if intelligence:
        pager.body(intelligence.summary)
        written = False
        for check in intelligence.logical_checks:
            if check.result in {"fail", "warning"}:
                pager.body(f"- {check.check_id}: {check.explanation}")
                written = True
        if not written:
            pager.body("No failed or warning logical checks were recorded.")
    else:
        pager.body("Document intelligence was not available.")

    pager.subhead("Key evidence images")
    embedded = 0
    for artifact_id in _collect_artifact_ids(fusion, ela, copy_move, intelligence)[:6]:
        try:
            path = resolve_artifact_path(settings, record.id, artifact_id)
        except HTTPException:
            continue
        pager.image(str(path), f"Evidence reference: {artifact_id}")
        embedded += 1
    if embedded == 0:
        pager.body("No evidence images were available to embed.")

    pager.subhead("Limitations")
    if fusion and fusion.limitations:
        for note in fusion.limitations:
            pager.body(f"- {note}")
    else:
        pager.body("No additional limitations were recorded.")

    pager.subhead("Disclaimer")
    pager.body(DISCLAIMER)

    page_count = pager.doc.page_count
    for index, page in enumerate(pager.doc, start=1):
        page.insert_text(
            (48, 820),
            f"DocuVerify · confidential forensic report · page {index} of {page_count}",
            fontsize=8,
            fontname="helv",
            color=(0.45, 0.42, 0.38),
        )

    extracted = "".join(page.get_text() for page in pager.doc).lower()
    for phrase in FORBIDDEN:
        if phrase in extracted:
            pager.doc.close()
            raise RuntimeError("Report contained forbidden certainty language.")
    data = pager.doc.tobytes()
    pager.doc.close()
    return data


def _collect_artifact_ids(fusion, ela, copy_move, intelligence) -> list[str]:
    ids: list[str] = []
    if fusion:
        for item in fusion.top_findings:
            if item.evidence_reference:
                ids.append(item.evidence_reference)
    if ela:
        for page in ela.pages:
            for evidence in page.evidence:
                ids.append(evidence.artifact_id)
    if copy_move:
        for page in copy_move.pages:
            for evidence in page.evidence:
                ids.append(evidence.artifact_id)
    if intelligence:
        for check in intelligence.logical_checks:
            if check.artifact_id:
                ids.append(check.artifact_id)
    unique: list[str] = []
    seen: set[str] = set()
    for artifact_id in ids:
        if artifact_id not in seen:
            seen.add(artifact_id)
            unique.append(artifact_id)
    return unique

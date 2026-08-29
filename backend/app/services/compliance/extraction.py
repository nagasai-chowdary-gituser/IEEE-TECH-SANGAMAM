from __future__ import annotations

import re

from app.schemas.compliance import CertificateFields, ExtractedIdentifier
from app.schemas.intelligence import ExtractionResult

PAN_BODY = re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]")
GSTIN_BODY = re.compile(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]")
PAN_RE = re.compile(r"\b(" + PAN_BODY.pattern + r")\b")
GSTIN_RE = re.compile(r"\b(" + GSTIN_BODY.pattern + r")\b")
PAN_LABELED = re.compile(r"\bPAN\b[\s:.\-]*([A-Z0-9]{10})\b", re.IGNORECASE)
GSTIN_LABELED = re.compile(r"\bGSTIN\b[\s:.\-]*([A-Z0-9]{15})\b", re.IGNORECASE)
UDYAM_RE = re.compile(r"\b(UDYAM-[A-Z]{2}-\d{2}-\d{7})\b", re.IGNORECASE)
NAME_RE = re.compile(
    r"(?:name\s+of\s+(?:enterprise|organisation|organization)|enterprise\s*name|name\s+of\s+unit)\s*[:\-]\s*([A-Za-z0-9][A-Za-z0-9 .,&'\-]{2,80})",
    re.IGNORECASE,
)
DATE_RE = re.compile(
    r"(?:date\s+of\s+(?:incorporation|registration|commencement))\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)

MIN_CONFIDENCE = 0.58


def is_valid_pan(value: str) -> bool:
    return bool(PAN_BODY.fullmatch(value.strip().upper())) if value else False


def is_valid_gstin(value: str) -> bool:
    return bool(GSTIN_BODY.fullmatch(value.strip().upper())) if value else False


def extract_udyam_fields(extraction: ExtractionResult) -> CertificateFields:
    blob = "\n".join(page.text for page in extraction.pages)
    pan = _best_identifier(extraction, (PAN_RE, PAN_LABELED), "pan", is_valid_pan)
    gstin = _best_identifier(extraction, (GSTIN_RE, GSTIN_LABELED), "gstin", is_valid_gstin)
    udyam = _first(UDYAM_RE, blob)
    name = _first(NAME_RE, blob)
    reg_date = _first(DATE_RE, blob)
    limitations: list[str] = []
    if extraction.overall_quality in {"low", "failed"}:
        limitations.append("Certificate text extraction quality was limited; identifier confidence may be reduced.")
    if pan.value is None:
        limitations.append("PAN was not extracted from the certificate.")
    if gstin.value is None:
        limitations.append("GSTIN was not extracted from the certificate.")
    return CertificateFields(
        pan=pan,
        gstin=gstin,
        udyam_number=udyam.upper() if udyam else None,
        enterprise_name=name,
        registration_date=reg_date,
        limitations=limitations,
    )


def _first(pattern: re.Pattern[str], blob: str) -> str | None:
    match = pattern.search(blob)
    if not match:
        return None
    return match.group(1).strip()


def _best_identifier(
    extraction: ExtractionResult,
    patterns: re.Pattern[str] | tuple[re.Pattern[str], ...],
    kind: str,
    validator,
) -> ExtractedIdentifier:
    compiled = patterns if isinstance(patterns, tuple) else (patterns,)
    candidates: list[ExtractedIdentifier] = []
    for page in extraction.pages:
        haystack = page.text.upper() if kind in {"pan", "gstin"} else page.text
        for pattern in compiled:
            for match in pattern.finditer(haystack):
                value = match.group(1).upper()
                confidence = page.confidence if page.source == "ocr" else 0.92
                if page.quality == "low":
                    confidence *= 0.7
                if page.quality == "failed":
                    continue
                if confidence < MIN_CONFIDENCE:
                    continue
                format_status = "valid" if validator(value) else "invalid"
                snippet = match.group(0)[:80]
                candidates.append(
                    ExtractedIdentifier(
                        kind=kind,  # type: ignore[arg-type]
                        value=value,
                        format_status=format_status,  # type: ignore[arg-type]
                        confidence=round(confidence, 4),
                        source_page=page.page_number,
                        snippet=snippet,
                    )
                )
    valid = [item for item in candidates if item.format_status == "valid"]
    pool = valid or candidates
    if not pool:
        return ExtractedIdentifier(kind=kind, value=None, format_status="not_extracted")  # type: ignore[arg-type]
    pool.sort(key=lambda item: item.confidence or 0, reverse=True)
    return pool[0]

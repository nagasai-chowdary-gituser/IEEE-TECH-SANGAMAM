from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import fitz
from PIL import Image, ExifTags
from pypdf import PdfReader

from app.schemas.metadata import MetadataForensicsResult, MetadataSignal
from app.services.forensics import scoring as rules

EXIF_TAGS = {v: k for k, v in ExifTags.TAGS.items()}
PDF_DATE_RE = re.compile(
    r"D:(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})"
    r"(?P<H>\d{2})?(?P<M>\d{2})?(?P<S>\d{2})?"
)


def analyze_metadata(file_path: str, document_type: str) -> MetadataForensicsResult:
    path = Path(file_path)
    if document_type in {"native_pdf", "scanned_pdf"}:
        signals, observed_fields = _analyze_pdf(path)
    else:
        signals, observed_fields = _analyze_image(path)

    suspicion_score = min(100, sum(signal.score_impact for signal in signals))
    flagged = suspicion_score >= rules.FLAG_THRESHOLD or any(s.severity == "high" for s in signals)
    confidence = min(
        rules.CONFIDENCE_MAX,
        round(rules.CONFIDENCE_BASE + rules.CONFIDENCE_PER_FIELD * observed_fields, 2),
    )
    return MetadataForensicsResult(
        layer="metadata",
        suspicion_score=suspicion_score,
        flagged=flagged,
        confidence=confidence,
        signals=signals,
        summary=_summarize(signals, suspicion_score, document_type),
    )


def _summarize(signals: list[MetadataSignal], score: int, document_type: str) -> str:
    if not signals:
        return (
            "No metadata forensic signals were generated. Available metadata appears ordinary "
            "for this document type; this is not a determination of authenticity."
        )
    high = [s.finding for s in signals if s.severity == "high"]
    medium = [s.finding for s in signals if s.severity == "medium"]
    if high:
        lead = high[0]
    elif medium:
        lead = medium[0]
    else:
        lead = signals[0].finding
    return (
        f"{lead} Combined metadata suspicion is {score}/100 for this {document_type.replace('_', ' ')}. "
        "These signals are contextual evidence only and do not prove that the document was forged."
    )


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def _contains_any(text: str, needles: tuple[str, ...]) -> str | None:
    for needle in needles:
        if needle in text:
            return needle
    return None


def _parse_pdf_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    match = PDF_DATE_RE.search(raw)
    if not match:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    parts = match.groupdict()
    try:
        return datetime(
            int(parts["y"]),
            int(parts["m"]),
            int(parts["d"]),
            int(parts["H"] or 0),
            int(parts["M"] or 0),
            int(parts["S"] or 0),
        )
    except ValueError:
        return None


def _analyze_pdf(path: Path) -> tuple[list[MetadataSignal], int]:
    signals: list[MetadataSignal] = []
    observed = 0
    creator = producer = creation_raw = mod_raw = ""
    xmp_creator = xmp_producer = ""
    font_count = 0

    with fitz.open(path) as doc:
        meta = doc.metadata or {}
        creator = meta.get("creator") or ""
        producer = meta.get("producer") or ""
        creation_raw = meta.get("creationDate") or ""
        mod_raw = meta.get("modDate") or ""
        for page in doc:
            font_count += len(page.get_fonts() or [])

    try:
        reader = PdfReader(str(path))
        info = reader.metadata
        if info is not None:
            creator = creator or str(info.creator or "")
            producer = producer or str(info.producer or "")
            creation_raw = creation_raw or str(info.creation_date or info.get("/CreationDate") or "")
            mod_raw = mod_raw or str(info.modification_date or info.get("/ModDate") or "")
        xmp = reader.xmp_metadata
        if xmp is not None:
            xmp_creator = " ".join(xmp.dc_creator or []) if getattr(xmp, "dc_creator", None) else ""
            xmp_producer = str(getattr(xmp, "pdf_producer", None) or "")
    except Exception:
        pass

    if creator:
        observed += 1
    if producer:
        observed += 1
    if creation_raw:
        observed += 1
    if mod_raw:
        observed += 1
    if font_count:
        observed += 1
    if xmp_creator or xmp_producer:
        observed += 1

    if not creator:
        signals.append(
            MetadataSignal(
                id="pdf_missing_creator",
                finding="Creator metadata is missing.",
                severity="low",
                score_impact=rules.SCORE_MISSING_CREATOR,
                detail="The PDF info dictionary does not include a Creator value. Missing creator is common and is weak evidence on its own.",
            )
        )
    if not producer:
        signals.append(
            MetadataSignal(
                id="pdf_missing_producer",
                finding="Producer metadata is missing.",
                severity="low",
                score_impact=rules.SCORE_MISSING_PRODUCER,
                detail="The PDF info dictionary does not include a Producer value. This is weak evidence and often occurs with stripped or minimal files.",
            )
        )
    if not creation_raw:
        signals.append(
            MetadataSignal(
                id="pdf_missing_creation_date",
                finding="Creation date is missing.",
                severity="low",
                score_impact=rules.SCORE_MISSING_CREATION_DATE,
                detail="No CreationDate was found. Absence of a timestamp is not proof of tampering.",
            )
        )
    if not mod_raw:
        signals.append(
            MetadataSignal(
                id="pdf_missing_mod_date",
                finding="Modification date is missing.",
                severity="low",
                score_impact=rules.SCORE_MISSING_MOD_DATE,
                detail="No ModDate was found. This is a weak signal.",
            )
        )

    present_count = sum(bool(v) for v in (creator, producer, creation_raw, mod_raw))
    if present_count == 0:
        signals.append(
            MetadataSignal(
                id="pdf_stripped_metadata",
                finding="PDF document information appears stripped or never written.",
                severity="low",
                score_impact=rules.SCORE_STRIPPED_METADATA,
                detail="Creator, Producer, CreationDate, and ModDate are all absent. Stripped metadata can occur for privacy, tooling, or export reasons and is not proof of forgery.",
            )
        )

    combined = f"{creator} {producer} {xmp_creator} {xmp_producer}".lower()
    high_hit = _contains_any(combined, rules.HIGH_RISK_EDITORS)
    medium_hit = _contains_any(combined, rules.MEDIUM_RISK_EDITORS)
    rewrite_hit = _contains_any(combined, rules.PDF_REWRITE_TOOLS)
    ordinary = _contains_any(combined, rules.ORDINARY_PRODUCERS)

    if high_hit:
        signals.append(
            MetadataSignal(
                id="pdf_known_editing_software",
                finding="Known image or document editing software appears in PDF metadata.",
                severity="medium",
                score_impact=rules.SCORE_HIGH_RISK_EDITOR,
                detail=f"Creator/Producer metadata references '{high_hit}'. This is suspicious context for a document file but does not by itself prove manipulation.",
            )
        )
    elif medium_hit:
        signals.append(
            MetadataSignal(
                id="pdf_known_editing_software",
                finding="Creative or editing software appears in PDF metadata.",
                severity="medium",
                score_impact=rules.SCORE_MEDIUM_RISK_EDITOR,
                detail=f"Creator/Producer metadata references '{medium_hit}'. This software can be used for legitimate design export as well as alteration.",
            )
        )
    elif rewrite_hit:
        signals.append(
            MetadataSignal(
                id="pdf_rewrite_tool",
                finding="A PDF rewriting or online conversion tool appears in metadata.",
                severity="medium",
                score_impact=rules.SCORE_PDF_REWRITE_TOOL,
                detail=f"Producer/Creator metadata references '{rewrite_hit}'. Online PDF tools commonly rewrite files and can change metadata without implying forgery.",
            )
        )

    creator_n = _normalize(creator)
    producer_n = _normalize(producer)
    if creator_n and producer_n and creator_n != producer_n:
        creator_editor = _contains_any(creator_n, rules.HIGH_RISK_EDITORS + rules.MEDIUM_RISK_EDITORS)
        producer_ordinary = ordinary and not _contains_any(producer_n, rules.HIGH_RISK_EDITORS)
        if creator_editor and producer_ordinary:
            signals.append(
                MetadataSignal(
                    id="pdf_creator_producer_conflict",
                    finding="Creator and Producer software identities do not align.",
                    severity="medium",
                    score_impact=rules.SCORE_CREATOR_PRODUCER_CONFLICT,
                    detail=f"Creator indicates '{creator_editor}' while Producer appears to be a different toolchain. Divergent identities can occur after export, round-tripping, or later editing.",
                )
            )

    created = _parse_pdf_date(str(creation_raw) if creation_raw else None)
    modified = _parse_pdf_date(str(mod_raw) if mod_raw else None)
    if created and modified:
        if modified < created:
            signals.append(
                MetadataSignal(
                    id="pdf_timestamp_mod_before_create",
                    finding="Modification timestamp precedes creation timestamp.",
                    severity="high",
                    score_impact=rules.SCORE_MOD_BEFORE_CREATE,
                    detail="ModDate is earlier than CreationDate. This is a strong inconsistency in the embedded timestamps, though clocks and time zones can also produce errors.",
                )
            )
        elif (modified - created).total_seconds() > 24 * 3600:
            signals.append(
                MetadataSignal(
                    id="pdf_post_creation_modification",
                    finding="Metadata indicates the file was modified after creation.",
                    severity="medium",
                    score_impact=rules.SCORE_MEANINGFUL_POST_EDIT,
                    detail="ModDate is more than 24 hours after CreationDate. Later modification is common (re-save, print, or metadata update) and is not proof of content tampering.",
                )
            )

    if (xmp_creator or xmp_producer) and (creator or producer):
        xmp_blob = f"{xmp_creator} {xmp_producer}".lower()
        info_blob = f"{creator} {producer}".lower()
        if xmp_blob.strip() and info_blob.strip() and xmp_blob not in info_blob and info_blob not in xmp_blob:
            if _contains_any(xmp_blob, rules.HIGH_RISK_EDITORS) or _contains_any(info_blob, rules.HIGH_RISK_EDITORS):
                signals.append(
                    MetadataSignal(
                        id="pdf_xmp_info_mismatch",
                        finding="XMP metadata does not match the PDF info dictionary.",
                        severity="medium",
                        score_impact=rules.SCORE_XMP_INFO_MISMATCH,
                        detail="Creator/Producer values in XMP differ from the document information dictionary. Conflicting metadata streams can appear after software round-trips.",
                    )
                )

    return signals, observed


def _analyze_image(path: Path) -> tuple[list[MetadataSignal], int]:
    signals: list[MetadataSignal] = []
    observed = 0
    software = ""
    datetime_original = ""
    datetime_digitized = ""
    datetime_generic = ""

    with Image.open(path) as image:
        exif = image.getexif()
        if exif:
            observed += 1
            software = str(exif.get(EXIF_TAGS.get("Software", 305), "") or "")
            datetime_generic = str(exif.get(EXIF_TAGS.get("DateTime", 306), "") or "")
            try:
                ifd = exif.get_ifd(0x8769)
            except Exception:
                ifd = {}
            datetime_original = str(ifd.get(EXIF_TAGS.get("DateTimeOriginal", 36867), "") or "")
            datetime_digitized = str(ifd.get(EXIF_TAGS.get("DateTimeDigitized", 36868), "") or "")

    if software:
        observed += 1
    if datetime_generic or datetime_original or datetime_digitized:
        observed += 1

    if observed == 0:
        signals.append(
            MetadataSignal(
                id="image_missing_exif",
                finding="No EXIF metadata was found.",
                severity="low",
                score_impact=rules.SCORE_MISSING_EXIF,
                detail="The image has no EXIF payload. Many legitimate exports, messaging apps, and screenshots omit EXIF. This is weak evidence.",
            )
        )
        return signals, observed

    if not software:
        signals.append(
            MetadataSignal(
                id="image_missing_software_tag",
                finding="EXIF Software tag is missing.",
                severity="low",
                score_impact=rules.SCORE_MISSING_IMAGE_SOFTWARE,
                detail="EXIF is present but does not name the creating software. This is a weak signal.",
            )
        )
    else:
        hit = _contains_any(software.lower(), rules.HIGH_RISK_EDITORS)
        medium = _contains_any(software.lower(), rules.MEDIUM_RISK_EDITORS)
        if hit:
            signals.append(
                MetadataSignal(
                    id="image_known_editing_software",
                    finding="Known image editing software appears in EXIF.",
                    severity="medium",
                    score_impact=rules.SCORE_HIGH_RISK_EDITOR,
                    detail=f"EXIF Software tag references '{hit}'. Edited-camera or exported images often include this tag; it is not proof that content was fabricated.",
                )
            )
        elif medium:
            signals.append(
                MetadataSignal(
                    id="image_known_editing_software",
                    finding="Creative software appears in EXIF.",
                    severity="medium",
                    score_impact=rules.SCORE_MEDIUM_RISK_EDITOR,
                    detail=f"EXIF Software tag references '{medium}'. This is contextual and not a determination of authenticity.",
                )
            )

    dates = [d for d in (datetime_generic, datetime_original, datetime_digitized) if d]
    if not dates:
        signals.append(
            MetadataSignal(
                id="image_missing_datetime",
                finding="EXIF date/time fields are missing.",
                severity="low",
                score_impact=rules.SCORE_MISSING_IMAGE_DATETIME,
                detail="No DateTime, DateTimeOriginal, or DateTimeDigitized values were found. Missing timestamps are common after re-encoding.",
            )
        )
    elif len(set(dates)) > 1:
        signals.append(
            MetadataSignal(
                id="image_exif_timestamp_mismatch",
                finding="EXIF date/time fields do not agree with each other.",
                severity="high",
                score_impact=rules.SCORE_EXIF_TIMESTAMP_MISMATCH,
                detail=f"Observed EXIF timestamps differ: {', '.join(sorted(set(dates)))}. Conflicting timestamps can indicate later processing, but cameras and converters also write inconsistent values.",
            )
        )

    return signals, observed

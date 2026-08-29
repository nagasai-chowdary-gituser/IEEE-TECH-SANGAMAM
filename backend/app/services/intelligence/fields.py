from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from datetime import date, datetime

from app.schemas.intelligence import ExtractedField, ExtractedPage, ExtractionResult, FieldEvidence
from app.schemas.visual import BoundingBox
from app.services.intelligence.config import MIN_FIELD_CONFIDENCE

DATE_PATTERN = (
    r"(?P<d>\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})"
)
MONEY = r"(?P<money>[$€£]?\s?-?\d{1,3}(?:,\d{3})*(?:\.\d{2})?|-?\d+\.\d{2})"

LABELED: list[tuple[str, str, str]] = [
    ("date_of_birth", r"(?:date\s*of\s*birth|d\.?o\.?b\.?|born(?:\s*on)?)\s*[:\-]?\s*" + DATE_PATTERN, "date"),
    ("age", r"\bage\s*[:\-]?\s*(?P<age>\d{1,3})\b", "int"),
    ("invoice_number", r"invoice\s*(?:no\.?|number|#)\s*[:\-]?\s*(?P<id>[A-Z0-9][A-Z0-9\-\/]{2,30})", "id"),
    ("document_number", r"(?:document|cert(?:ificate)?|registration)\s*(?:no\.?|number|#)\s*[:\-]?\s*(?P<id>[A-Z0-9][A-Z0-9\-\/]{2,30})", "id"),
    ("issue_date", r"(?:issue\s*date|date\s*of\s*issue|issued(?:\s*on)?)\s*[:\-]?\s*" + DATE_PATTERN, "date"),
    ("due_date", r"(?:due\s*date|payment\s*due)\s*[:\-]?\s*" + DATE_PATTERN, "date"),
    ("expiry_date", r"(?:expir(?:y|ation)\s*date|valid\s*until)\s*[:\-]?\s*" + DATE_PATTERN, "date"),
    ("subtotal", r"^sub\s*-?\s*total\s*[:\-]?\s*" + MONEY, "money"),
    ("tax", r"^(?:tax|vat|gst)\s*(?:amount)?\s*[:\-]?\s*" + MONEY, "money"),
    ("total", r"^(?:grand\s+)?total\s*[:\-]?\s*" + MONEY, "money"),
    ("amount", r"^(?:amount\s*due|amount)\s*[:\-]?\s*" + MONEY, "money"),
    ("quantity", r"^(?:quantity|qty)\s*[:\-]?\s*(?P<qty>\d+(?:\.\d+)?)", "number"),
    ("unit_price", r"^unit\s*price\s*[:\-]?\s*" + MONEY, "money"),
    ("line_total", r"^line\s+total\s*[:\-]?\s*" + MONEY, "money"),
    ("percentage", r"(?:rate|percent(?:age)?)\s*[:\-]?\s*(?P<pct>\d+(?:\.\d+)?)\s*%", "percent"),
    ("name", r"(?:full\s*)?name\s*[:\-]?\s*(?P<name>[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})", "name"),
]


def extract_fields(extraction: ExtractionResult) -> list[ExtractedField]:
    fields: list[ExtractedField] = []
    counters: dict[str, int] = {}
    for page in extraction.pages:
        blob = page.text
        if not blob.strip():
            continue
        for field_type, pattern, kind in LABELED:
            for match in re.finditer(pattern, blob, flags=re.IGNORECASE | re.MULTILINE):
                raw, normalized = _value_from_match(match, kind)
                if raw is None:
                    continue
                confidence = _field_confidence(page, kind)
                if confidence < MIN_FIELD_CONFIDENCE:
                    continue
                counters[field_type] = counters.get(field_type, 0) + 1
                bbox = _locate_value(page, raw)
                fields.append(
                    ExtractedField(
                        field_id=f"{field_type}_{counters[field_type]:02d}",
                        field_type=field_type,
                        value=raw,
                        normalized_value=normalized,
                        page_number=page.page_number,
                        confidence=confidence,
                        source=page.source,
                        evidence=FieldEvidence(
                            label=field_type.replace("_", " "),
                            bbox=bbox,
                            snippet=match.group(0)[:120],
                        ),
                    )
                )
    return fields


def _field_confidence(page: ExtractedPage, kind: str) -> float:
    base = page.confidence if page.source == "ocr" else 0.92
    if page.quality == "low":
        base *= 0.7
    if page.quality == "failed":
        return 0.0
    if kind == "name":
        base *= 0.9
    return round(min(0.98, max(0.0, base)), 3)


def _value_from_match(match: re.Match, kind: str) -> tuple[str | None, object | None]:
    groups = match.groupdict()
    if kind == "date":
        raw = groups.get("d") or match.group(0)
        parsed = parse_date(raw)
        if parsed is None:
            return None, None
        return raw.strip(), parsed.isoformat()
    if kind == "money":
        raw = (groups.get("money") or "").strip()
        amount = parse_money(raw)
        if amount is None:
            return None, None
        return raw, float(amount)
    if kind == "int":
        raw = groups.get("age") or ""
        if not raw.isdigit():
            return None, None
        value = int(raw)
        if value > 120:
            return None, None
        return raw, value
    if kind == "number":
        raw = groups.get("qty") or ""
        try:
            return raw, float(raw)
        except ValueError:
            return None, None
    if kind == "percent":
        raw = groups.get("pct") or ""
        try:
            return f"{raw}%", float(raw)
        except ValueError:
            return None, None
    if kind == "id":
        raw = (groups.get("id") or "").strip()
        if len(raw) < 3:
            return None, None
        return raw, raw.upper()
    if kind == "name":
        raw = (groups.get("name") or "").strip()
        if len(raw.split()) < 1:
            return None, None
        return raw, raw
    return None, None


def parse_money(raw: str) -> Decimal | None:
    cleaned = re.sub(r"[^\d.\-]", "", raw or "")
    if cleaned in {"", "-", "."}:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_date(raw: str) -> date | None:
    text = (raw or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d/%m/%y", "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _locate_value(page: ExtractedPage, value: str) -> BoundingBox | None:
    needle = value.strip()
    if not needle:
        return None
    for token in page.tokens:
        if needle in token.text or token.text in needle:
            return token.bbox
    pieces = needle.split()
    if len(pieces) >= 2:
        for token in page.tokens:
            if token.text == pieces[0] and token.bbox:
                return token.bbox
    return None

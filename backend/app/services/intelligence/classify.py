from __future__ import annotations

from app.schemas.intelligence import DocumentClassification, ExtractedField, ExtractionResult

INVOICE_HINTS = ("invoice", "subtotal", "qty", "unit price", "amount due", "tax")
CERTIFICATE_HINTS = ("certificate", "date of birth", "awarded", "hereby certify", "diploma")


def classify_document(extraction: ExtractionResult, fields: list[ExtractedField]) -> DocumentClassification:
    text = " ".join(page.text.lower() for page in extraction.pages)
    field_types = {f.field_type for f in fields}
    invoice_hits = sum(1 for hint in INVOICE_HINTS if hint in text)
    cert_hits = sum(1 for hint in CERTIFICATE_HINTS if hint in text)
    if "invoice_number" in field_types or "subtotal" in field_types:
        invoice_hits += 2
    if "date_of_birth" in field_types and "invoice_number" not in field_types:
        cert_hits += 2
    if invoice_hits >= 2 and invoice_hits > cert_hits:
        return DocumentClassification(
            document_class="invoice",
            confidence=min(0.9, 0.5 + 0.1 * invoice_hits),
            rationale="Invoice labels and/or monetary fields were found in the extracted text.",
        )
    if cert_hits >= 2 and cert_hits > invoice_hits:
        return DocumentClassification(
            document_class="certificate",
            confidence=min(0.88, 0.5 + 0.1 * cert_hits),
            rationale="Certificate-style labels were found in the extracted text.",
        )
    return DocumentClassification(
        document_class="generic_document",
        confidence=0.4,
        rationale="No confident invoice or certificate pattern was identified; generic checks still apply.",
    )

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal

from app.schemas.intelligence import (
    CheckEvidence,
    ExtractedField,
    ExtractionResult,
    LogicalCheck,
)
from app.services.intelligence.config import (
    MONEY_TOLERANCE,
    SCORE_ARITHMETIC_FAIL,
    SCORE_DATE_ORDER_FAIL,
    SCORE_DOB_AGE_FAIL,
    SCORE_DUPLICATE_FAIL,
    SCORE_IDENTIFIER_FAIL,
    SCORE_QR_CONFLICT,
    WARNING_FACTOR,
)
from app.services.intelligence.fields import parse_date, parse_money


def run_logical_checks(
    extraction: ExtractionResult,
    fields: list[ExtractedField],
    barcode_values: list[tuple[str, int]] | None = None,
) -> list[LogicalCheck]:
    checks: list[LogicalCheck] = []
    by_type = _group(fields)
    checks.append(_dob_age(by_type, extraction))
    checks.append(_date_order(by_type))
    checks.extend(_invoice_arithmetic(by_type, extraction))
    checks.append(_duplicates(by_type))
    checks.append(_identifier_format(by_type))
    checks.append(_barcode_conflict(by_type, barcode_values or []))
    return checks


def _group(fields: list[ExtractedField]) -> dict[str, list[ExtractedField]]:
    grouped: dict[str, list[ExtractedField]] = defaultdict(list)
    for field in fields:
        grouped[field.field_type].append(field)
    return grouped


def _first(by_type: dict[str, list[ExtractedField]], key: str) -> ExtractedField | None:
    items = by_type.get(key) or []
    return items[0] if items else None


def _dob_age(by_type: dict[str, list[ExtractedField]], extraction: ExtractionResult) -> LogicalCheck:
    dob_field = _first(by_type, "date_of_birth")
    age_field = _first(by_type, "age")
    if not dob_field or not age_field:
        return LogicalCheck(
            check_id="dob_age_consistency",
            category="identity",
            result="insufficient_data",
            severity="low",
            score_impact=0,
            confidence=0.4,
            explanation="DOB and age were not both confidently extracted, so the check was not evaluated.",
        )
    dob = parse_date(str(dob_field.normalized_value or dob_field.value))
    try:
        stated_age = int(age_field.normalized_value if age_field.normalized_value is not None else age_field.value)
    except (TypeError, ValueError):
        dob = None
        stated_age = None
    if dob is None or stated_age is None:
        return LogicalCheck(
            check_id="dob_age_consistency",
            category="identity",
            result="insufficient_data",
            severity="low",
            score_impact=0,
            confidence=0.4,
            explanation="DOB or age could not be parsed reliably.",
        )
    issue = _first(by_type, "issue_date")
    used_today = False
    if issue and issue.normalized_value:
        ref = parse_date(str(issue.normalized_value)) or date.fromisoformat(str(issue.normalized_value)[:10])
    else:
        ref = datetime.now(timezone.utc).date()
        used_today = True
    calculated = _age_on(dob, ref)
    conf = min(dob_field.confidence, age_field.confidence)
    if used_today:
        conf = min(conf, 0.55)
    evidence = CheckEvidence(
        expected=calculated,
        observed=stated_age,
        bbox=age_field.evidence.bbox if age_field.evidence else None,
        page_number=age_field.page_number,
        extra={"dob": dob.isoformat(), "reference_date": ref.isoformat(), "used_current_date": used_today},
    )
    limitation = " Age was compared to the current date because no document issue date was extracted." if used_today else ""
    if stated_age == calculated:
        return LogicalCheck(
            check_id="dob_age_consistency",
            category="identity",
            result="pass",
            severity="low",
            score_impact=0,
            confidence=conf,
            evidence=evidence,
            explanation=f"Stated age {stated_age} matches age calculated from DOB {dob.isoformat()} as of {ref.isoformat()}.{limitation}",
        )
    # Birthday-boundary: already handled by _age_on. Off-by-one with current-date fallback is a warning.
    if used_today and abs(stated_age - calculated) == 1:
        return LogicalCheck(
            check_id="dob_age_consistency",
            category="identity",
            result="warning",
            severity="low",
            score_impact=int(SCORE_DOB_AGE_FAIL * WARNING_FACTOR),
            confidence=conf,
            evidence=evidence,
            explanation=f"Stated age {stated_age} differs by one year from DOB-derived age {calculated} using today's date as a limited fallback.{limitation}",
        )
    return LogicalCheck(
        check_id="dob_age_consistency",
        category="identity",
        result="fail",
        severity="high",
        score_impact=SCORE_DOB_AGE_FAIL,
        confidence=conf,
        evidence=evidence,
        explanation=f"Stated age {stated_age} does not match age {calculated} calculated from DOB {dob.isoformat()} as of {ref.isoformat()}.{limitation}",
    )


def _age_on(dob: date, ref: date) -> int:
    years = ref.year - dob.year
    if (ref.month, ref.day) < (dob.month, dob.day):
        years -= 1
    return years


def _date_order(by_type: dict[str, list[ExtractedField]]) -> LogicalCheck:
    issue = _parse_field_date(_first(by_type, "issue_date"))
    due = _parse_field_date(_first(by_type, "due_date"))
    expiry = _parse_field_date(_first(by_type, "expiry_date"))
    if issue is None and due is None and expiry is None:
        return LogicalCheck(
            check_id="date_order_consistency",
            category="temporal",
            result="insufficient_data",
            severity="low",
            score_impact=0,
            confidence=0.35,
            explanation="Not enough dated fields were extracted to evaluate chronological order.",
        )
    conflicts: list[str] = []
    if issue and due and due < issue:
        conflicts.append(f"due date {due.isoformat()} is before issue date {issue.isoformat()}")
    if issue and expiry and expiry < issue:
        conflicts.append(f"expiry date {expiry.isoformat()} is before issue date {issue.isoformat()}")
    if not conflicts:
        return LogicalCheck(
            check_id="date_order_consistency",
            category="temporal",
            result="pass" if (issue and (due or expiry)) else "not_applicable",
            severity="low",
            score_impact=0,
            confidence=0.7 if issue else 0.4,
            explanation="No invalid chronological order was found among extracted dates."
            if issue and (due or expiry)
            else "A comparable date pair was not present.",
        )
    field = _first(by_type, "due_date") or _first(by_type, "expiry_date")
    return LogicalCheck(
        check_id="date_order_consistency",
        category="temporal",
        result="fail",
        severity="medium",
        score_impact=SCORE_DATE_ORDER_FAIL,
        confidence=0.75,
        evidence=CheckEvidence(
            expected="issue_date <= later dates",
            observed="; ".join(conflicts),
            bbox=field.evidence.bbox if field and field.evidence else None,
            page_number=field.page_number if field else None,
        ),
        explanation="An extracted date sequence is not logically valid: " + "; ".join(conflicts) + ".",
    )


def _parse_field_date(field: ExtractedField | None) -> date | None:
    if not field:
        return None
    if field.normalized_value:
        parsed = parse_date(str(field.normalized_value))
        if parsed:
            return parsed
    return parse_date(field.value)


def _invoice_arithmetic(by_type: dict[str, list[ExtractedField]], extraction: ExtractionResult) -> list[LogicalCheck]:
    checks: list[LogicalCheck] = []
    qty = _moneyish(_first(by_type, "quantity"))
    unit = _moneyish(_first(by_type, "unit_price"))
    line = _moneyish(_first(by_type, "line_total"))
    if qty is not None and unit is not None and line is not None:
        expected = qty * unit
        mismatch = abs(expected - line) > MONEY_TOLERANCE
        field = _first(by_type, "line_total")
        conf = min(f.confidence for f in [_first(by_type, "quantity"), _first(by_type, "unit_price"), field] if f)
        if extraction.overall_quality == "low":
            conf = min(conf, 0.45)
        checks.append(
            LogicalCheck(
                check_id="line_item_arithmetic",
                category="arithmetic",
                result="fail" if mismatch else "pass",
                severity="high" if mismatch else "low",
                score_impact=SCORE_ARITHMETIC_FAIL if mismatch else 0,
                confidence=conf,
                evidence=CheckEvidence(
                    expected=float(expected),
                    observed=float(line),
                    bbox=field.evidence.bbox if field and field.evidence else None,
                    page_number=field.page_number if field else None,
                ),
                explanation=(
                    f"Quantity × unit price ({float(expected):.2f}) does not match line total ({float(line):.2f})."
                    if mismatch
                    else "Quantity × unit price matches the extracted line total within rounding tolerance."
                ),
            )
        )
    else:
        checks.append(
            LogicalCheck(
                check_id="line_item_arithmetic",
                category="arithmetic",
                result="insufficient_data",
                severity="low",
                score_impact=0,
                confidence=0.35,
                explanation="Quantity, unit price, and line total were not all extracted, so the line-item check was not evaluated.",
            )
        )

    subtotal = _moneyish(_first(by_type, "subtotal"))
    tax = _moneyish(_first(by_type, "tax"))
    total = _moneyish(_first(by_type, "total")) or _moneyish(_first(by_type, "amount"))
    line_sum = None
    line_fields = by_type.get("line_total") or []
    if len(line_fields) >= 1 and subtotal is not None:
        amounts = [_moneyish(f) for f in line_fields]
        if all(a is not None for a in amounts):
            line_sum = sum(amounts)  # type: ignore[arg-type]

    if line_sum is not None and subtotal is not None:
        mismatch = abs(line_sum - subtotal) > MONEY_TOLERANCE
        checks.append(
            LogicalCheck(
                check_id="subtotal_consistency",
                category="arithmetic",
                result="fail" if mismatch else "pass",
                severity="high" if mismatch else "low",
                score_impact=SCORE_ARITHMETIC_FAIL if mismatch else 0,
                confidence=0.7,
                evidence=CheckEvidence(expected=float(line_sum), observed=float(subtotal)),
                explanation=(
                    "The sum of line totals does not match the extracted subtotal."
                    if mismatch
                    else "The sum of line totals matches the extracted subtotal within rounding tolerance."
                ),
            )
        )
    elif subtotal is None:
        checks.append(
            LogicalCheck(
                check_id="subtotal_consistency",
                category="arithmetic",
                result="insufficient_data",
                severity="low",
                score_impact=0,
                confidence=0.3,
                explanation="A subtotal was not extracted, so the subtotal check was not evaluated.",
            )
        )

    if subtotal is not None and total is not None:
        expected = subtotal + (tax if tax is not None else Decimal("0"))
        mismatch = abs(expected - total) > MONEY_TOLERANCE
        field = _first(by_type, "total") or _first(by_type, "amount")
        conf = min((f.confidence for f in [_first(by_type, "subtotal"), field] if f), default=0.5)
        if extraction.overall_quality == "low":
            conf = min(conf, 0.45)
        checks.append(
            LogicalCheck(
                check_id="invoice_total_consistency",
                category="arithmetic",
                result="fail" if mismatch else "pass",
                severity="high" if mismatch else "low",
                score_impact=SCORE_ARITHMETIC_FAIL if mismatch else 0,
                confidence=conf,
                evidence=CheckEvidence(
                    expected=float(expected),
                    observed=float(total),
                    bbox=field.evidence.bbox if field and field.evidence else None,
                    page_number=field.page_number if field else None,
                    extra={"subtotal": float(subtotal), "tax": float(tax) if tax is not None else None},
                ),
                explanation=(
                    f"The displayed total does not match subtotal + tax ({float(expected):.2f} vs {float(total):.2f})."
                    if mismatch
                    else "Subtotal + tax matches the extracted total within rounding tolerance."
                ),
            )
        )
    else:
        checks.append(
            LogicalCheck(
                check_id="invoice_total_consistency",
                category="arithmetic",
                result="insufficient_data",
                severity="low",
                score_impact=0,
                confidence=0.3,
                explanation="Subtotal and total were not both extracted, so the total check was not evaluated.",
            )
        )
    return checks


def _moneyish(field: ExtractedField | None) -> Decimal | None:
    if not field:
        return None
    if isinstance(field.normalized_value, (int, float)):
        return Decimal(str(field.normalized_value))
    return parse_money(field.value)


def _duplicates(by_type: dict[str, list[ExtractedField]]) -> LogicalCheck:
    tracked = ("invoice_number", "total", "date_of_birth", "document_number")
    conflicts: list[str] = []
    bbox = None
    page_number = None
    for key in tracked:
        values = []
        for field in by_type.get(key, []):
            norm = str(field.normalized_value if field.normalized_value is not None else field.value).strip().upper()
            if norm not in values:
                values.append(norm)
            if len(values) > 1:
                conflicts.append(f"{key} has conflicting values {values}")
                bbox = field.evidence.bbox if field.evidence else bbox
                page_number = field.page_number
                break
    if not any(len(by_type.get(k, [])) >= 2 for k in tracked):
        return LogicalCheck(
            check_id="duplicate_field_consistency",
            category="consistency",
            result="not_applicable",
            severity="low",
            score_impact=0,
            confidence=0.5,
            explanation="No repeated identity of the same field was found to compare.",
        )
    if not conflicts:
        return LogicalCheck(
            check_id="duplicate_field_consistency",
            category="consistency",
            result="pass",
            severity="low",
            score_impact=0,
            confidence=0.72,
            explanation="Repeated fields that were identified carry the same value.",
        )
    return LogicalCheck(
        check_id="duplicate_field_consistency",
        category="consistency",
        result="fail",
        severity="high",
        score_impact=SCORE_DUPLICATE_FAIL,
        confidence=0.78,
        evidence=CheckEvidence(observed="; ".join(conflicts), bbox=bbox, page_number=page_number),
        explanation="The same field appears with contradictory values: " + "; ".join(conflicts) + ".",
    )


def _identifier_format(by_type: dict[str, list[ExtractedField]]) -> LogicalCheck:
    issues: list[str] = []
    for key in ("invoice_number", "document_number"):
        items = by_type.get(key) or []
        if len(items) < 2:
            continue
        patterns = { _id_shape(f.value) for f in items }
        if len(patterns) > 1:
            issues.append(f"{key} uses inconsistent internal formats {sorted(patterns)}")
    dob = _first(by_type, "date_of_birth")
    if dob and parse_date(dob.value) is None and parse_date(str(dob.normalized_value or "")) is None:
        issues.append("date of birth value is malformed")
    if not issues:
        if not any(by_type.get(k) for k in ("invoice_number", "document_number", "date_of_birth")):
            return LogicalCheck(
                check_id="identifier_format_consistency",
                category="format",
                result="insufficient_data",
                severity="low",
                score_impact=0,
                confidence=0.3,
                explanation="No recognizable identifiers were extracted for format comparison.",
            )
        return LogicalCheck(
            check_id="identifier_format_consistency",
            category="format",
            result="pass",
            severity="low",
            score_impact=0,
            confidence=0.6,
            explanation="Extracted identifiers are internally well-formed. This is not an external registry check.",
        )
    return LogicalCheck(
        check_id="identifier_format_consistency",
        category="format",
        result="fail",
        severity="medium",
        score_impact=SCORE_IDENTIFIER_FAIL,
        confidence=0.65,
        evidence=CheckEvidence(observed="; ".join(issues)),
        explanation="Internal identifier formatting is inconsistent: " + "; ".join(issues) + ". This does not mean the identifier is unregistered.",
    )


def _id_shape(value: str) -> str:
    return "".join("A" if ch.isalpha() else ("0" if ch.isdigit() else ch) for ch in value.strip().upper())


def _barcode_conflict(by_type: dict[str, list[ExtractedField]], barcodes: list[tuple[str, int]]) -> LogicalCheck:
    if not barcodes:
        return LogicalCheck(
            check_id="barcode_field_consistency",
            category="barcode",
            result="not_applicable",
            severity="low",
            score_impact=0,
            confidence=0.4,
            explanation="No QR/barcode payload was decoded, so no comparison was performed.",
        )
    visible = []
    for key in ("invoice_number", "document_number"):
        visible.extend(str(f.normalized_value or f.value).upper() for f in by_type.get(key, []))
    payload = barcodes[0][0].strip().upper()
    if not visible:
        return LogicalCheck(
            check_id="barcode_field_consistency",
            category="barcode",
            result="insufficient_data",
            severity="low",
            score_impact=0,
            confidence=0.45,
            evidence=CheckEvidence(observed=payload, extra={"page_number": barcodes[0][1]}),
            explanation="QR/barcode data was decoded but no comparable printed identifier was extracted.",
        )
    if any(v and (v in payload or payload in v) for v in visible):
        return LogicalCheck(
            check_id="barcode_field_consistency",
            category="barcode",
            result="pass",
            severity="low",
            score_impact=0,
            confidence=0.7,
            evidence=CheckEvidence(expected=visible[0], observed=payload),
            explanation="Decoded QR/barcode content is consistent with a printed identifier. This does not confirm authenticity.",
        )
    return LogicalCheck(
        check_id="barcode_field_consistency",
        category="barcode",
        result="fail",
        severity="high",
        score_impact=SCORE_QR_CONFLICT,
        confidence=0.72,
        evidence=CheckEvidence(expected=visible[0], observed=payload, page_number=barcodes[0][1]),
        explanation="QR/barcode content conflicts with visible printed identifier values.",
    )

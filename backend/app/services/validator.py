"""Validation engine.

Runs deterministic checks on extracted data. Every issue has a field name and a
severity (error or warning). Errors put the document into "Needs Review" status.
"""
from datetime import date, datetime
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models import Document
from app.schemas import ExtractedData, ValidationIssue


# Tolerance for floating-point comparisons of money. Most invoices round to 2 decimals,
# so anything within 0.02 is fine. We also allow 0.5% relative tolerance for very large invoices.
ABSOLUTE_TOLERANCE = 0.02
RELATIVE_TOLERANCE = 0.005


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(ABSOLUTE_TOLERANCE, abs(b) * RELATIVE_TOLERANCE)


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def validate(
    data: ExtractedData,
    db: Optional[Session] = None,
    current_document_id: Optional[int] = None,
) -> list[ValidationIssue]:
    """Run all validation checks. db + current_document_id enable duplicate detection."""
    issues: list[ValidationIssue] = []

    issues.extend(_check_document_type(data))
    issues.extend(_check_missing_required_fields(data))
    issues.extend(_check_dates(data))
    issues.extend(_check_line_item_math(data))
    issues.extend(_check_totals(data))
    if db is not None:
        issues.extend(_check_duplicates(data, db, current_document_id))

    return issues


def _check_document_type(data: ExtractedData) -> Iterable[ValidationIssue]:
    if data.document_type in (None, "unknown"):
        yield ValidationIssue(
            field="document_type",
            severity="error",
            message="Document could not be identified as an invoice or purchase order.",
        )


def _check_missing_required_fields(data: ExtractedData) -> Iterable[ValidationIssue]:
    """Flag empty fields. Severity depends on how critical the field is."""
    critical = {
        "supplier_name": data.supplier_name,
        "document_number": data.document_number,
        "total": data.total,
    }
    nice_to_have = {
        "issue_date": data.issue_date,
        "currency": data.currency,
    }
    for field, value in critical.items():
        if value is None or (isinstance(value, str) and not value.strip()):
            yield ValidationIssue(field=field, severity="error", message=f"Missing required field: {field}.")
    for field, value in nice_to_have.items():
        if value is None or (isinstance(value, str) and not value.strip()):
            yield ValidationIssue(field=field, severity="warning", message=f"Missing field: {field}.")


def _check_dates(data: ExtractedData) -> Iterable[ValidationIssue]:
    issue_date = _parse_iso_date(data.issue_date)
    due_date = _parse_iso_date(data.due_date)

    if data.issue_date and not issue_date:
        yield ValidationIssue(
            field="issue_date",
            severity="error",
            message=f"Issue date '{data.issue_date}' is not a valid date.",
        )
    if data.due_date and not due_date:
        yield ValidationIssue(
            field="due_date",
            severity="error",
            message=f"Due date '{data.due_date}' is not a valid date.",
        )

    # Logical ordering
    if issue_date and due_date and due_date < issue_date:
        yield ValidationIssue(
            field="due_date",
            severity="error",
            message="Due date is before issue date.",
        )

    # Future-dated issue is suspicious but not always wrong (some systems pre-date).
    # Warn rather than error to keep humans in the loop.
    if issue_date and issue_date > date.today():
        yield ValidationIssue(
            field="issue_date",
            severity="warning",
            message="Issue date is in the future.",
        )


def _check_line_item_math(data: ExtractedData) -> Iterable[ValidationIssue]:
    """For each line item where quantity, unit_price, and total are present, verify total = qty * price."""
    for idx, item in enumerate(data.line_items):
        if item.quantity is not None and item.unit_price is not None and item.total is not None:
            expected = item.quantity * item.unit_price
            if not _close(expected, item.total):
                yield ValidationIssue(
                    field=f"line_items[{idx}].total",
                    severity="error",
                    message=(
                        f"Line {idx + 1}: quantity ({item.quantity}) x unit price ({item.unit_price}) "
                        f"= {expected:.2f}, but total is {item.total}."
                    ),
                )


def _check_totals(data: ExtractedData) -> Iterable[ValidationIssue]:
    """subtotal + tax should equal total; sum of line items should equal subtotal."""
    # subtotal + tax == total
    if data.subtotal is not None and data.tax is not None and data.total is not None:
        expected = data.subtotal + data.tax
        if not _close(expected, data.total):
            yield ValidationIssue(
                field="total",
                severity="error",
                message=(
                    f"Subtotal ({data.subtotal}) + tax ({data.tax}) = {expected:.2f}, "
                    f"but total is {data.total}."
                ),
            )

    # sum(line_items.total) == subtotal
    items_with_totals = [it.total for it in data.line_items if it.total is not None]
    if items_with_totals and data.subtotal is not None:
        line_sum = sum(items_with_totals)
        if not _close(line_sum, data.subtotal):
            yield ValidationIssue(
                field="subtotal",
                severity="warning",
                message=(
                    f"Sum of line item totals ({line_sum:.2f}) does not match "
                    f"subtotal ({data.subtotal})."
                ),
            )


def _check_duplicates(
    data: ExtractedData, db: Session, current_document_id: Optional[int]
) -> Iterable[ValidationIssue]:
    if not data.document_number:
        return
    query = db.query(Document).filter(
        Document.id != (current_document_id or -1),
    )
    for existing in query.all():
        existing_data = existing.extracted_data or {}
        if (
            existing_data.get("document_number") == data.document_number
            and existing_data.get("supplier_name") == data.supplier_name
            and data.supplier_name is not None
        ):
            yield ValidationIssue(
                field="document_number",
                severity="error",
                message=(
                    f"Duplicate document number '{data.document_number}' for supplier "
                    f"'{data.supplier_name}' (existing doc id {existing.id})."
                ),
            )
            return


def derive_status_after_validation(issues: list[ValidationIssue]) -> str:
    """Decide the initial status based on validation outcome."""
    from app.models import STATUS_NEEDS_REVIEW, STATUS_UPLOADED
    has_errors = any(i.severity == "error" for i in issues)
    return STATUS_NEEDS_REVIEW if has_errors else STATUS_UPLOADED

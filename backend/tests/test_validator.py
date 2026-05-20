"""Tests for the validation engine.

We test the validator in isolation (no Gemini, no DB) because the take-home
explicitly mentions "include your own validation logic" — this is the layer
they will scrutinize.
"""
from app.schemas import ExtractedData, LineItem
from app.services.validator import validate


def _has_issue(issues, field: str, severity: str | None = None) -> bool:
    return any(i.field == field and (severity is None or i.severity == severity) for i in issues)


def test_clean_invoice_has_no_errors():
    data = ExtractedData(
        document_type="invoice",
        supplier_name="ACME",
        document_number="INV-1",
        issue_date="2026-01-01",
        currency="EUR",
        line_items=[LineItem(description="X", quantity=2, unit_price=50, total=100)],
        subtotal=100,
        tax=20,
        total=120,
    )
    issues = validate(data)
    errors = [i for i in issues if i.severity == "error"]
    assert errors == [], f"Expected no errors, got: {errors}"


def test_wrong_total_is_detected():
    """Mirrors the deliberate bug in invoice_1.pdf: 645 + 129 != 800."""
    data = ExtractedData(
        document_type="invoice",
        supplier_name="Company 0",
        document_number="INV-1000",
        issue_date="2026-04-28",
        currency="EUR",
        line_items=[LineItem(description="Service A", quantity=5, unit_price=129, total=645)],
        subtotal=645,
        tax=129.0,
        total=800.0,
    )
    issues = validate(data)
    assert _has_issue(issues, "total", "error")


def test_missing_required_fields_are_errors():
    data = ExtractedData(document_type="invoice")
    issues = validate(data)
    assert _has_issue(issues, "supplier_name", "error")
    assert _has_issue(issues, "document_number", "error")
    assert _has_issue(issues, "total", "error")


def test_unknown_document_type_is_error():
    data = ExtractedData(document_type="unknown")
    issues = validate(data)
    assert _has_issue(issues, "document_type", "error")


def test_due_date_before_issue_date_is_error():
    data = ExtractedData(
        document_type="invoice",
        supplier_name="A",
        document_number="1",
        issue_date="2026-05-10",
        due_date="2026-05-01",
        total=100,
    )
    issues = validate(data)
    assert _has_issue(issues, "due_date", "error")


def test_line_item_math_is_validated():
    data = ExtractedData(
        document_type="invoice",
        supplier_name="A",
        document_number="1",
        issue_date="2026-01-01",
        currency="EUR",
        line_items=[LineItem(description="X", quantity=3, unit_price=10, total=99)],  # should be 30
        total=99,
        subtotal=99,
        tax=0,
    )
    issues = validate(data)
    assert _has_issue(issues, "line_items[0].total", "error")


def test_floating_point_tolerance():
    """1/3 of 100 rounded to cents — totals must allow tiny floating-point slack."""
    data = ExtractedData(
        document_type="invoice",
        supplier_name="A",
        document_number="1",
        issue_date="2026-01-01",
        currency="EUR",
        line_items=[LineItem(quantity=3, unit_price=33.33, total=99.99)],
        subtotal=99.99,
        tax=20.00,
        total=119.99,
    )
    issues = validate(data)
    errors = [i for i in issues if i.severity == "error"]
    assert errors == []

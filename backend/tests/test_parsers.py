"""Tests for file parsers.

We test against the actual sample files committed under tests/fixtures/ so
the test is meaningful — not just mocking everything away.
"""
from pathlib import Path

import pytest

from app.parsers.csv_parser import parse_csv, _safe_float
from app.parsers.txt_parser import parse_txt
from app.parsers.pdf_parser import parse_pdf

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.skipif(not (FIXTURES / "data_1.csv").exists(), reason="fixture missing")
def test_csv_parses_with_line_items():
    result = parse_csv(FIXTURES / "data_1.csv")
    assert result.error is None
    assert "line_items" in result.hint
    items = result.hint["line_items"]
    assert len(items) == 2
    assert items[0]["total"] == 78.0
    assert items[1]["total"] == 168.0


@pytest.mark.skipif(not (FIXTURES / "text_1.txt").exists(), reason="fixture missing")
def test_txt_reads_content():
    result = parse_txt(FIXTURES / "text_1.txt")
    assert result.error is None
    assert "Total" in result.raw_text


@pytest.mark.skipif(not (FIXTURES / "invoice_1.pdf").exists(), reason="fixture missing")
def test_pdf_extracts_invoice_text():
    result = parse_pdf(FIXTURES / "invoice_1.pdf")
    assert result.error is None
    assert "INV-1000" in result.raw_text or "Invoice" in result.raw_text


def test_safe_float_eu_format():
    assert _safe_float("1.234,56") == 1234.56


def test_safe_float_us_format():
    assert _safe_float("1,234.56") == 1234.56


def test_safe_float_handles_currency_symbol():
    assert _safe_float("€ 100,50") == 100.50


def test_safe_float_returns_none_for_garbage():
    assert _safe_float("abc") is None
    assert _safe_float("") is None
    assert _safe_float(None) is None

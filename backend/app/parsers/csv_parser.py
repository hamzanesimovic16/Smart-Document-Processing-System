"""CSV parser.

CSV files in our dataset typically contain only line items, no header metadata
like supplier or date. We:
  1) Auto-detect delimiter and encoding (different sources use different conventions)
  2) Map common column-name variants to our canonical schema
  3) Produce a hint dict with structured line items the LLM stage can use directly

The LLM is still called afterwards in case the CSV has additional context rows
(some CSVs have "Supplier: X" or "Total: Y" as free text rows above the table).
"""
import logging
from pathlib import Path

import pandas as pd

from app.parsers.base import ParseResult

logger = logging.getLogger(__name__)


# Map of canonical-name → list of variant header names we recognise.
# Lowercased + stripped for case-insensitive matching.
COLUMN_ALIASES: dict[str, list[str]] = {
    "description": ["description", "desc", "item", "product", "name", "details"],
    "quantity": ["quantity", "qty", "amount", "count"],
    "unit_price": ["unit_price", "unitprice", "price", "rate", "unit price", "unit cost"],
    "total": ["total", "amount", "line_total", "line total", "subtotal", "value"],
}


def _detect_encoding_and_read(file_path: Path) -> pd.DataFrame:
    """Try common encodings + delimiters in order. UTF-8 first, then fall back."""
    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    last_exc: Exception | None = None
    for encoding in encodings:
        try:
            # sep=None + engine='python' makes pandas sniff the delimiter (, ; \t |)
            return pd.read_csv(file_path, encoding=encoding, sep=None, engine="python")
        except (UnicodeDecodeError, pd.errors.ParserError) as exc:
            last_exc = exc
            continue
    raise last_exc or RuntimeError("Could not read CSV with any known encoding")


def _normalize_column(col: str) -> str:
    return col.strip().lower().replace("-", "_").replace(" ", "_")


def _map_columns(df: pd.DataFrame) -> dict[str, str]:
    """Return a mapping from canonical name to the actual column in the dataframe."""
    found: dict[str, str] = {}
    normalized = {_normalize_column(c): c for c in df.columns}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = _normalize_column(alias)
            if key in normalized:
                found[canonical] = normalized[key]
                break
    return found


def _safe_float(value) -> float | None:
    """Convert a cell to float, handling both '1.234,56' (EU) and '1,234.56' (US)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if not s:
        return None
    # Strip non-numeric characters except separators and minus
    s = "".join(ch for ch in s if ch.isdigit() or ch in ".,-")
    if not s:
        return None
    # If both separators are present, the last one is the decimal separator
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        # Heuristic: a single comma with 1-2 digits after it is a decimal separator
        decimals = len(s.split(",")[-1])
        s = s.replace(",", "." if decimals in (1, 2) else "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_csv(file_path: Path) -> ParseResult:
    try:
        df = _detect_encoding_and_read(file_path)
    except Exception as exc:
        logger.exception("Failed to read CSV %s", file_path)
        return ParseResult(raw_text="", error=f"CSV read failed: {exc}")

    column_map = _map_columns(df)

    # Build structured line items where we can recognise columns.
    line_items: list[dict] = []
    if column_map:
        for _, row in df.iterrows():
            item = {
                "description": str(row[column_map["description"]]) if "description" in column_map else None,
                "quantity": _safe_float(row[column_map["quantity"]]) if "quantity" in column_map else None,
                "unit_price": _safe_float(row[column_map["unit_price"]]) if "unit_price" in column_map else None,
                "total": _safe_float(row[column_map["total"]]) if "total" in column_map else None,
            }
            # Drop completely empty rows
            if any(v is not None and v != "" for v in item.values()):
                line_items.append(item)

    # Raw text representation for the LLM — keeps formatting predictable.
    raw_text = df.to_csv(index=False)

    hint = {}
    if line_items:
        hint["line_items"] = line_items

    return ParseResult(raw_text=raw_text, hint=hint)

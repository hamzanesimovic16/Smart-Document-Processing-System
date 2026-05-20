"""Document extractor orchestrator.

Picks the right parser for a file type, runs it, feeds the raw text to Gemini,
and runs validation. Returns (extracted_data, validation_issues, raw_text, error).
"""
import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.parsers.base import ParseResult
from app.parsers.csv_parser import parse_csv
from app.parsers.image_parser import parse_image
from app.parsers.pdf_parser import parse_pdf
from app.parsers.txt_parser import parse_txt
from app.schemas import ExtractedData, ValidationIssue
from app.services.gemini import extract_from_text
from app.services.validator import validate

logger = logging.getLogger(__name__)


# File extension → (parser function, canonical type label)
PARSER_REGISTRY = {
    ".pdf": (parse_pdf, "pdf"),
    ".png": (parse_image, "image"),
    ".jpg": (parse_image, "image"),
    ".jpeg": (parse_image, "image"),
    ".webp": (parse_image, "image"),
    ".csv": (parse_csv, "csv"),
    ".txt": (parse_txt, "txt"),
}


def get_file_type(filename: str) -> Optional[str]:
    """Return our canonical file-type label, or None for unsupported extensions."""
    ext = Path(filename).suffix.lower()
    entry = PARSER_REGISTRY.get(ext)
    return entry[1] if entry else None


def process_document(
    file_path: Path,
    db: Optional[Session] = None,
    current_document_id: Optional[int] = None,
) -> tuple[ExtractedData, list[ValidationIssue], str, Optional[str]]:
    ext = file_path.suffix.lower()
    entry = PARSER_REGISTRY.get(ext)
    if not entry:
        return (
            ExtractedData(document_type="unknown"),
            [ValidationIssue(field="_general", severity="error", message=f"Unsupported file type: {ext}")],
            "",
            f"Unsupported file type: {ext}",
        )

    parser_fn, _ = entry
    result: ParseResult = parser_fn(file_path)

    if result.error and not result.raw_text:
        # Parser failed and we have no text — short-circuit with the parser error.
        extracted = ExtractedData(document_type="unknown")
        issues = validate(extracted, db=db, current_document_id=current_document_id)
        issues.insert(0, ValidationIssue(field="_general", severity="error", message=result.error))
        return extracted, issues, "", result.error

    extracted = extract_from_text(result.raw_text, hint=result.hint)
    issues = validate(extracted, db=db, current_document_id=current_document_id)
    return extracted, issues, result.raw_text, result.error

"""PDF parser.

We use pdfplumber because our test PDFs are text-based (born-digital).
For scanned PDFs we would need to rasterize each page and run OCR — listed
as an improvement in the README but not implemented to keep scope tight.
"""
import logging
from pathlib import Path

import pdfplumber

from app.parsers.base import ParseResult

logger = logging.getLogger(__name__)


def parse_pdf(file_path: Path) -> ParseResult:
    try:
        text_parts: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text)

        raw_text = "\n\n".join(text_parts).strip()

        if not raw_text:
            # Likely a scanned PDF — log and return empty so the LLM has nothing to hallucinate from.
            logger.warning("PDF %s yielded no text (likely scanned).", file_path.name)
            return ParseResult(
                raw_text="",
                error="No text found in PDF. The file may be a scan — OCR support is not implemented.",
            )

        return ParseResult(raw_text=raw_text)
    except Exception as exc:
        logger.exception("Failed to parse PDF %s", file_path)
        return ParseResult(raw_text="", error=f"PDF parse failed: {exc}")

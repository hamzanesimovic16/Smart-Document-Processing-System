"""Image parser via Tesseract OCR.

Tesseract is a binary that must be installed separately on the system.
On Windows, the path must be configured via TESSERACT_CMD env var if not on PATH.
"""
import logging
from pathlib import Path

import pytesseract
from PIL import Image

from app.config import settings
from app.parsers.base import ParseResult

logger = logging.getLogger(__name__)

# Configure tesseract executable path if provided (Windows typically needs this).
if settings.tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def parse_image(file_path: Path) -> ParseResult:
    try:
        with Image.open(file_path) as img:
            # Convert to grayscale — improves OCR on simple documents.
            gray = img.convert("L")
            raw_text = pytesseract.image_to_string(gray, lang="eng")

        raw_text = raw_text.strip()
        if not raw_text:
            return ParseResult(
                raw_text="",
                error="OCR returned no text. The image may be blank or low quality.",
            )
        return ParseResult(raw_text=raw_text)
    except pytesseract.TesseractNotFoundError:
        msg = (
            "Tesseract binary not found. Install Tesseract OCR and set TESSERACT_CMD "
            "in .env if not on PATH."
        )
        logger.error(msg)
        return ParseResult(raw_text="", error=msg)
    except Exception as exc:
        logger.exception("Failed to OCR image %s", file_path)
        return ParseResult(raw_text="", error=f"OCR failed: {exc}")

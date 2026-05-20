"""TXT parser. Try common encodings until one succeeds."""
import logging
from pathlib import Path

from app.parsers.base import ParseResult

logger = logging.getLogger(__name__)


def parse_txt(file_path: Path) -> ParseResult:
    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    for encoding in encodings:
        try:
            text = file_path.read_text(encoding=encoding).strip()
            return ParseResult(raw_text=text)
        except UnicodeDecodeError:
            continue
        except Exception as exc:
            logger.exception("Failed to read TXT %s", file_path)
            return ParseResult(raw_text="", error=f"TXT read failed: {exc}")
    return ParseResult(raw_text="", error="Could not decode TXT with any known encoding")

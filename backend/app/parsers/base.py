"""Common parser interface.

Every parser reads a file path and returns:
  - raw_text: plain text representation of the file (for the LLM to extract from)
  - hint: optional pre-extracted structured fields (CSV already has structure, so we use it)

Hint lets us combine deterministic parsing where possible with LLM extraction
where the document has no obvious structure.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParseResult:
    raw_text: str
    hint: dict = field(default_factory=dict)
    error: Optional[str] = None

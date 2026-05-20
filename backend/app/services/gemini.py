"""Gemini extraction service (using the new google-genai SDK).

The legacy google-generativeai package was deprecated in favour of google-genai.
We send raw text from the parser to Gemini and ask for structured JSON matching
our ExtractedData schema. Two important behaviours:

1) We use response_mime_type='application/json' so Gemini returns valid JSON.
2) The system prompt explicitly forbids inventing data — missing fields must be null.
   This is critical: the task says "validate or set null on empty fields", so we
   must never hallucinate.

If the API call fails, we return an empty ExtractedData with document_type='unknown'
so downstream validation can flag the document for manual review.
"""
import json
import time
import logging
from typing import Optional

from google import genai
from google.genai import types as genai_types

from app.config import settings
from app.schemas import ExtractedData, LineItem

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You extract structured data from business documents (invoices and purchase orders).

CRITICAL RULES:
- Return ONLY valid JSON matching the requested schema. No prose, no markdown fences.
- Never invent data. If a field is not clearly present in the text, return null.
- For document_type: "invoice" if the document is an invoice/bill/receipt, "purchase_order" if it is a PO/order, "unknown" if you cannot tell or the document is not invoice/PO.
- Dates must be in ISO format YYYY-MM-DD. If the year, month or day is ambiguous, return null.
- Currency must be a 3-letter ISO code (EUR, USD, BAM, GBP, ...) if you can determine it, else null.
- Numbers must be raw numbers without currency symbols or thousand separators.
- line_items can be an empty array if none are present.
- supplier_name is the company issuing the invoice or making the order. Do not confuse it with the buyer.

Output schema:
{
  "document_type": "invoice" | "purchase_order" | "unknown" | null,
  "supplier_name": string | null,
  "document_number": string | null,
  "issue_date": "YYYY-MM-DD" | null,
  "due_date": "YYYY-MM-DD" | null,
  "currency": string | null,
  "line_items": [
    { "description": string | null, "quantity": number | null, "unit_price": number | null, "total": number | null }
  ],
  "subtotal": number | null,
  "tax": number | null,
  "total": number | null
}
"""


_client: Optional[genai.Client] = None


def _get_client() -> Optional[genai.Client]:
    global _client
    if _client is not None:
        return _client
    if not settings.gemini_api_key:
        logger.error("GEMINI_API_KEY is not configured.")
        return None
    _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def extract_from_text(raw_text: str, hint: Optional[dict] = None) -> ExtractedData:
    """Send raw text to Gemini and return parsed ExtractedData. Never raises."""
    if not raw_text.strip():
        return ExtractedData(document_type="unknown")

    client = _get_client()
    if client is None:
        return ExtractedData(document_type="unknown")

    user_prompt = f"Extract structured data from this document:\n\n{raw_text}"
    if hint:
        user_prompt += f"\n\nPre-extracted hints (use these if reasonable):\n{json.dumps(hint)}"

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=user_prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            text = response.text or ""
            break
        except Exception as exc:
            if "429" in str(exc) and attempt < 2:
                time.sleep(5)
                continue
            logger.exception("Gemini API call failed")
            return ExtractedData(document_type="unknown")

    return _parse_gemini_response(text, hint)


def _parse_gemini_response(text: str, hint: Optional[dict]) -> ExtractedData:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Gemini returned non-JSON: %s", text[:200])
        return ExtractedData(document_type="unknown")

    if hint and hint.get("line_items") and not data.get("line_items"):
        data["line_items"] = hint["line_items"]

    try:
        return ExtractedData(**data)
    except Exception as exc:
        logger.error("Gemini output failed schema validation: %s", exc)
        return _salvage_partial(data)


def _salvage_partial(data: dict) -> ExtractedData:
    """If Gemini returns slightly off-schema data, keep what is valid."""
    safe: dict = {"line_items": []}
    string_fields = ["document_type", "supplier_name", "document_number", "issue_date", "due_date", "currency"]
    number_fields = ["subtotal", "tax", "total"]

    for f in string_fields:
        v = data.get(f)
        if isinstance(v, str) and v.strip():
            safe[f] = v.strip()

    for f in number_fields:
        v = data.get(f)
        if isinstance(v, (int, float)):
            safe[f] = float(v)

    items_raw = data.get("line_items") or []
    if isinstance(items_raw, list):
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            try:
                safe["line_items"].append(LineItem(**item))
            except Exception:
                continue

    if safe.get("document_type") not in ("invoice", "purchase_order", "unknown"):
        safe["document_type"] = "unknown"

    return ExtractedData(**safe)

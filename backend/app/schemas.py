from datetime import datetime, date
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


# ---- Extracted document data shape ----
# Every field is Optional — missing data must be null, never invented.

class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None


class ExtractedData(BaseModel):
    document_type: Optional[Literal["invoice", "purchase_order", "unknown"]] = None
    supplier_name: Optional[str] = None
    document_number: Optional[str] = None
    issue_date: Optional[str] = None  # ISO date string YYYY-MM-DD or null
    due_date: Optional[str] = None
    currency: Optional[str] = None  # e.g. EUR, USD, BAM
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None


# ---- Validation ----

class ValidationIssue(BaseModel):
    field: str  # which field the issue is on, or "_general"
    severity: Literal["error", "warning"]
    message: str


# ---- API response shapes ----

class DocumentSummary(BaseModel):
    """Used in the dashboard list view."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    file_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    # Convenience denormalized fields for the dashboard
    supplier_name: Optional[str] = None
    document_number: Optional[str] = None
    total: Optional[float] = None
    currency: Optional[str] = None
    issue_count: int = 0


class DocumentDetail(BaseModel):
    """Full document for the review screen."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    file_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    raw_text: Optional[str] = None
    extracted_data: ExtractedData
    validation_issues: list[ValidationIssue]


# ---- Request bodies ----

class UpdateExtractedDataRequest(BaseModel):
    extracted_data: ExtractedData


class UpdateStatusRequest(BaseModel):
    status: Literal["Uploaded", "Needs Review", "Validated", "Rejected"]

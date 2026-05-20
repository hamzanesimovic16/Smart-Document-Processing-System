"""HTTP API routes."""
import logging
from pydoc import doc
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import (
    ALL_STATUSES,
    STATUS_REJECTED,
    Document,
    STATUS_NEEDS_REVIEW,
    STATUS_UPLOADED,
    STATUS_VALIDATED,
)
from app.schemas import (
    DocumentDetail,
    DocumentSummary,
    ExtractedData,
    UpdateExtractedDataRequest,
    UpdateStatusRequest,
    ValidationIssue,
)
from app.services.extractor import get_file_type, process_document
from app.services.validator import derive_status_after_validation, validate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


# ---------- Helpers ----------

def _to_summary(doc: Document) -> DocumentSummary:
    data = doc.extracted_data or {}
    issues = doc.validation_issues or []
    return DocumentSummary(
        id=doc.id,
        original_filename=doc.original_filename,
        file_type=doc.file_type,
        status=doc.status,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        supplier_name=data.get("supplier_name"),
        document_number=data.get("document_number"),
        total=data.get("total"),
        currency=data.get("currency"),
        issue_count=len(issues),
    )


def _to_detail(doc: Document) -> DocumentDetail:
    return DocumentDetail(
        id=doc.id,
        original_filename=doc.original_filename,
        file_type=doc.file_type,
        status=doc.status,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        raw_text=doc.raw_text,
        extracted_data=ExtractedData(**(doc.extracted_data or {})),
        validation_issues=[ValidationIssue(**i) for i in (doc.validation_issues or [])],
    )


# ---------- Endpoints ----------

@router.post("/documents", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a file, parse it, extract data, validate, and save to DB."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_type = get_file_type(file.filename)
    if not file_type:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: PDF, PNG, JPG, JPEG, WEBP, CSV, TXT.",
        )

    # Persist the file with a unique name so re-uploads don't collide.
    suffix = Path(file.filename).suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    stored_path = settings.upload_dir / stored_name
    content = await file.read()
    stored_path.write_bytes(content)

    # Create row early so duplicate-check can exclude this document by id.
    doc = Document(
        original_filename=file.filename,
        stored_filename=stored_name,
        file_type=file_type,
        file_size=len(content),
        status=STATUS_UPLOADED,
        extracted_data={},
        validation_issues=[],
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    extracted, issues, raw_text, _parser_error = process_document(
        stored_path, db=db, current_document_id=doc.id
    )

    doc.raw_text = raw_text
    doc.extracted_data = extracted.model_dump()
    doc.validation_issues = [i.model_dump() for i in issues]
    doc.status = derive_status_after_validation(issues)
    db.commit()
    db.refresh(doc)

    return _to_detail(doc)


@router.get("/documents", response_model=list[DocumentSummary])
def list_documents(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Dashboard list. Optional ?status_filter=Validated."""
    query = db.query(Document).order_by(Document.created_at.desc())
    if status_filter:
        query = query.filter(Document.status == status_filter)
    return [_to_summary(d) for d in query.all()]


@router.get("/documents/stats")
def documents_stats(db: Session = Depends(get_db)):
    """Aggregate stats for the dashboard: status counts and totals grouped by currency."""
    docs = db.query(Document).all()
    status_counts = defaultdict(int)
    totals_by_currency: dict[str, float] = defaultdict(float)
    for d in docs:
        status_counts[d.status] += 1
        data = d.extracted_data or {}
        if d.status == STATUS_VALIDATED and data.get("total") is not None and data.get("currency"):
            totals_by_currency[data["currency"]] += float(data["total"])
    return {
        "total_documents": len(docs),
        "status_counts": dict(status_counts),
        "totals_by_currency": dict(totals_by_currency),
    }


@router.get("/documents/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _to_detail(doc)


@router.put("/documents/{doc_id}", response_model=DocumentDetail)
def update_document(
    doc_id: int,
    payload: UpdateExtractedDataRequest,
    db: Session = Depends(get_db),
):
    """Save manual corrections. Re-runs validation on the new data."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.extracted_data = payload.extracted_data.model_dump()
    issues = validate(payload.extracted_data, db=db, current_document_id=doc.id)
    doc.validation_issues = [i.model_dump() for i in issues]
    # If user corrected the document, move it to Needs Review until they explicitly confirm.
    has_errors = any(i.severity == "error" for i in issues)
    if has_errors:
        doc.status = STATUS_NEEDS_REVIEW
    elif doc.status not in (STATUS_VALIDATED, STATUS_REJECTED):
        doc.status = derive_status_after_validation(issues)
    db.commit()
    db.refresh(doc)
    return _to_detail(doc)


@router.put("/documents/{doc_id}/status", response_model=DocumentDetail)
def update_status(
    doc_id: int,
    payload: UpdateStatusRequest,
    db: Session = Depends(get_db),
):
    if payload.status not in ALL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {payload.status}")
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.status = payload.status
    db.commit()
    db.refresh(doc)
    return _to_detail(doc)

@router.get("/documents/{doc_id}/file")
def get_document_file(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    file_path = settings.upload_dir / doc.stored_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(
        path=file_path,
        filename=doc.original_filename,
        media_type="application/octet-stream"
    )

@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # Best-effort file cleanup
    try:
        (settings.upload_dir / doc.stored_filename).unlink(missing_ok=True)
    except Exception:
        pass
    db.delete(doc)
    db.commit()
    return None

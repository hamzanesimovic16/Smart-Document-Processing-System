from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text

from app.database import Base


# Status workflow values — kept as strings for SQLite simplicity
STATUS_UPLOADED = "Uploaded"
STATUS_NEEDS_REVIEW = "Needs Review"
STATUS_VALIDATED = "Validated"
STATUS_REJECTED = "Rejected"

ALL_STATUSES = [STATUS_UPLOADED, STATUS_NEEDS_REVIEW, STATUS_VALIDATED, STATUS_REJECTED]


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    # File metadata
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)  # unique name on disk
    file_type = Column(String, nullable=False)  # pdf | image | csv | txt
    file_size = Column(Integer, nullable=False)

    # Extraction
    raw_text = Column(Text, nullable=True)  # text we fed to Gemini, useful for debugging
    extracted_data = Column(JSON, nullable=False, default=dict)  # full extracted payload
    validation_issues = Column(JSON, nullable=False, default=list)  # list of issue dicts

    # Workflow
    status = Column(String, nullable=False, default=STATUS_UPLOADED)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

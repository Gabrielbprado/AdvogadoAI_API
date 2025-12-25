"""Domain models related to document ingestion and storage."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel


class DocumentProcessingError(RuntimeError):
    """Raised when a document cannot be processed."""


class DocumentMetadata(BaseModel):
    """Basic metadata captured during upload."""

    filename: str
    content_type: Optional[str] = None
    size_bytes: int


class DocumentRecord(BaseModel):
    """Internal representation of a stored document."""

    doc_id: str
    file_path: Path
    metadata: DocumentMetadata
    owner_id: int | None = None

    model_config = {"arbitrary_types_allowed": True}


class DocumentUploadResponse(BaseModel):
    """API response returned after uploading a document."""

    doc_id: str
    filename: str


class DocumentExtractionResult(BaseModel):
    """Result of reading and cleaning the document text."""

    doc_id: str
    text: str
    metadata: DocumentMetadata


class DocumentRepository:
    """Simple in-memory repository for storing document records."""

    def __init__(self) -> None:
        self._records: Dict[str, DocumentRecord] = {}

    def save(self, record: DocumentRecord) -> None:
        """Persist a document record in memory."""
        self._records[record.doc_id] = record

    def get(self, doc_id: str, *, owner_id: int | None = None) -> DocumentRecord:
        """Retrieve a document record or raise an error if absent or unauthorized."""
        try:
            record = self._records[doc_id]
        except KeyError as exc:
            raise DocumentProcessingError(f"Document {doc_id} not found") from exc

        if owner_id is not None and record.owner_id and record.owner_id != owner_id:
            raise DocumentProcessingError("Documento não pertence ao usuário autenticado")
        return record

    def exists(self, doc_id: str, *, owner_id: int | None = None) -> bool:
        """Return whether a document record exists and optionally belongs to the owner."""
        if doc_id not in self._records:
            return False
        if owner_id is None:
            return True
        record = self._records[doc_id]
        if record.owner_id is None:
            return True
        return record.owner_id == owner_id

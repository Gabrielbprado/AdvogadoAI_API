"""PDF handling service built on top of pdfplumber."""
from __future__ import annotations

from pathlib import Path

import pdfplumber
from logging import Logger

from app.domain.models.document_models import (
    DocumentExtractionResult,
    DocumentMetadata,
    DocumentProcessingError,
)


class PDFService:
    """Service responsible for extracting text from PDF documents."""

    def __init__(self, logger: Logger) -> None:
        self._logger = logger

    def extract_text(self, doc_id: str, file_path: Path, metadata: DocumentMetadata) -> DocumentExtractionResult:
        """Extract textual content from a PDF file."""
        try:
            with pdfplumber.open(file_path) as pdf:
                pages_text = [page.extract_text() or "" for page in pdf.pages]
        except Exception as exc:
            self._logger.error("Failed to read PDF %s: %s", doc_id, exc)
            raise DocumentProcessingError("Unable to read PDF file") from exc

        text = "\n".join(segment.strip() for segment in pages_text if segment).strip()
        if not text:
            raise DocumentProcessingError("No extractable text found in PDF")

        self._logger.info("PDF %s extracted with %d characters", doc_id, len(text))
        return DocumentExtractionResult(doc_id=doc_id, text=text, metadata=metadata)

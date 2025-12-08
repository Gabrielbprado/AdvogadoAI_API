"""Document-related API routes."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.domain.models.analysis_models import FinalAnalysisResponse
from app.domain.models.document_models import (
    DocumentMetadata,
    DocumentProcessingError,
    DocumentRecord,
    DocumentRepository,
    DocumentUploadResponse,
)
from app.infrastructure.langgraph.graph_builder import DocumentPipelineGraph
from app.utils.file_utils import ensure_directory, generate_document_id, save_upload_file
from app.utils.logger import get_logger


def build_document_router(
    *,
    repository: DocumentRepository,
    graph: DocumentPipelineGraph,
    storage_dir: Path,
) -> APIRouter:
    """Create and return the document router with injected dependencies."""
    router = APIRouter(prefix="/document", tags=["documentos"])
    logger = get_logger(__name__)

    @router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
    async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:

        doc_id = generate_document_id()
        ensure_directory(storage_dir)
        stored_path = save_upload_file(file, storage_dir, filename=f"{doc_id}.pdf")

        metadata = DocumentMetadata(
            filename=file.filename or f"{doc_id}.pdf",
            content_type=file.content_type,
            size_bytes=stored_path.stat().st_size,
        )
        repository.save(DocumentRecord(doc_id=doc_id, file_path=stored_path, metadata=metadata))
        return DocumentUploadResponse(doc_id=doc_id, filename=metadata.filename)

    @router.post("/analyze/{doc_id}", response_model=FinalAnalysisResponse)
    async def analyze_document(doc_id: str) -> FinalAnalysisResponse:
        try:
            return graph.run(doc_id)
        except DocumentProcessingError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ValueError as exc:
            logger.error("Crew output parsing failed: %s", exc)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        except Exception as exc: 
            logger.exception("Unexpected analysis failure")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno") from exc

    return router

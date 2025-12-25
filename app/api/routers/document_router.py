"""Document-related API routes."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.domain.models.analysis_models import FinalAnalysisResponse
from app.domain.models.document_models import (
    DocumentMetadata,
    DocumentProcessingError,
    DocumentRecord,
    DocumentRepository,
    DocumentUploadResponse,
)
from app.domain.models.user_models import DocumentAnalysisRequest
from app.domain.services.auth_service import AuthService
from app.domain.services.user_service import UserService
from app.domain.services.jurisprudence_service import JurisprudenceService
from app.infrastructure.langgraph.graph_builder import DocumentPipelineGraph
from app.infrastructure.db.entities import User
from app.api.security import oauth2_scheme
from app.utils.file_utils import ensure_directory, generate_document_id, save_upload_file
from app.utils.logger import get_logger


def build_document_router(
    *,
    repository: DocumentRepository,
    graph: DocumentPipelineGraph,
    storage_dir: Path,
    session_factory: Callable[..., Session],
    auth_service: AuthService,
    user_service: UserService,
    jurisprudence_service: JurisprudenceService | None = None,
) -> APIRouter:
    """Create and return the document router with injected dependencies."""
    router = APIRouter(prefix="/document", tags=["documentos"])
    logger = get_logger(__name__)

    def get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    async def get_current_user(
        token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
    ) -> User:
        email = auth_service.decode_token_subject(token)
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
        user = user_service.get_user_by_email(db, email)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
        return user

    @router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
    async def upload_document(
        file: UploadFile = File(...), current_user: User = Depends(get_current_user)
    ) -> DocumentUploadResponse:

        doc_id = generate_document_id()
        ensure_directory(storage_dir)
        stored_path = save_upload_file(file, storage_dir, filename=f"{doc_id}.pdf")

        metadata = DocumentMetadata(
            filename=file.filename or f"{doc_id}.pdf",
            content_type=file.content_type,
            size_bytes=stored_path.stat().st_size,
        )
        repository.save(
            DocumentRecord(
                doc_id=doc_id,
                file_path=stored_path,
                metadata=metadata,
                owner_id=current_user.id,
            )
        )
        return DocumentUploadResponse(doc_id=doc_id, filename=metadata.filename)

    @router.post("/analyze/{doc_id}", response_model=FinalAnalysisResponse)
    async def analyze_document(
        doc_id: str,
        payload: DocumentAnalysisRequest | None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> FinalAnalysisResponse:
        try:
            payload = payload or DocumentAnalysisRequest()
            template_text = None
            if payload.template_id is not None:
                template = user_service.get_template(db, current_user, payload.template_id)
                if not template:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo não encontrado")
                template_text = template.content

            instructions = payload.instructions_override if payload.instructions_override is not None else current_user.instructions
            avisos = payload.avisos_override if payload.avisos_override is not None else current_user.avisos

            user_context_parts = []
            if instructions:
                user_context_parts.append(f"Instruções do usuário: {instructions}")
            if avisos:
                user_context_parts.append(
                    "Avisos prioritários (observar com máxima atenção): " + avisos
                )
            if template_text:
                user_context_parts.append(f"Modelo de resposta selecionado: {template_text}")
            if payload.custom_request:
                user_context_parts.append(f"Pedido específico desta análise: {payload.custom_request}")

            user_context = "\n\n".join(user_context_parts) if user_context_parts else None

            result = graph.run(doc_id, owner_id=current_user.id, user_context=user_context)
            
            # Add jurisprudence links if service is available
            if jurisprudence_service:
                try:
                    # Extract legal terms from analysis
                    analysis_text = result.parecer.parecer_detalhado if hasattr(result, 'parecer') else str(result)
                    legal_terms = jurisprudence_service.extract_jurisprudence_terms(
                        document_content=analysis_text
                    )
                    
                    # Add jurisprudence to response
                    if legal_terms:
                        jurisprudence_links = jurisprudence_service.create_jurisprudence_response(legal_terms)
                        # Import the model
                        from app.domain.models.analysis_models import JurisprudenciaLink
                        # Convert to JurisprudenciaLink objects
                        result.jurisprudencia = [
                            JurisprudenciaLink(
                                termo=link["term"],
                                url=link["url"],
                                fonte=link.get("source", "Jusbrasil")
                            )
                            for link in jurisprudence_links
                        ]
                        logger.info(f"Added {len(result.jurisprudencia)} jurisprudence links to analysis")
                except Exception as jur_exc:
                    logger.warning(f"Error adding jurisprudence: {jur_exc}")
                    # Continue without jurisprudence if there's an error
            
            return result
        except DocumentProcessingError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ValueError as exc:
            logger.error("Crew output parsing failed: %s", exc)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        except Exception as exc: 
            logger.exception("Unexpected analysis failure")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno") from exc

    return router

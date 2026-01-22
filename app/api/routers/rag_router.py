"""RAG-related API routes for legal document question answering."""
from __future__ import annotations

from typing import Callable, Optional, List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.domain.services.rag_service import RAGService
from app.domain.services.jurisprudence_service import JurisprudenceService
from app.domain.models.document_models import DocumentRecord, DocumentRepository, DocumentProcessingError
from app.infrastructure.db.entities import User
from app.api.security import oauth2_scheme
from app.domain.services.auth_service import AuthService
from app.domain.services.user_service import UserService
from app.utils.logger import get_logger


# Request/Response Models
class RAGQuestionRequest(BaseModel):
    """Request model for RAG question answering."""
    question: str = Field(..., description="Pergunta sobre o documento jurídico")
    doc_id: Optional[str] = Field(None, description="ID do documento para pesquisar (opcional para busca global)")


class RAGDocumentQuestionRequest(BaseModel):
    """Request model for RAG question answering scoped to one document."""
    question: str = Field(..., description="Pergunta sobre o documento jurídico")
    auto_ingest: bool = Field(
        True,
        description="Se verdadeiro, ingere automaticamente o documento caso ainda não esteja no índice",
    )


class JurisprudenceLink(BaseModel):
    """Model for jurisprudence link."""
    termo: str = Field(..., description="Termo jurídico")
    url: str = Field(..., description="URL de pesquisa no Jusbrasil")
    descricao: str = Field(..., description="Descrição do termo")
    fonte: str = Field(..., description="Fonte da jurisprudência")


class RAGSourceChunk(BaseModel):
    """Source chunk from RAG retrieval."""
    text: str = Field(..., description="Texto do trecho do documento")
    similarity: float = Field(..., description="Score de similaridade (0-1)")
    doc_id: str = Field(..., description="ID do documento")


class RAGAnswerResponse(BaseModel):
    """Response model for RAG question answering."""
    answer: str = Field(..., description="Resposta baseada no documento")
    sources: List[RAGSourceChunk] = Field(default_factory=list, description="Trechos do documento usados")
    legal_context: Optional[str] = Field(None, description="Contexto jurídico")
    jurisprudencia: List[JurisprudenceLink] = Field(default_factory=list, description="Links para jurisprudência")


class DocumentSummaryResponse(BaseModel):
    """Response model for document summary."""
    doc_id: str = Field(..., description="ID do documento")
    summary: str = Field(..., description="Resumo do documento")
    chunk_count: int = Field(..., description="Número de trechos do documento")
    jurisprudencia: List[JurisprudenceLink] = Field(default_factory=list, description="Links para jurisprudência")


def build_rag_router(
    *,
    rag_service: RAGService,
    jurisprudence_service: JurisprudenceService,
    repository: DocumentRepository,
    session_factory: Callable[..., Session],
    auth_service: AuthService,
    user_service: UserService,
) -> APIRouter:
    """Create and return the RAG router with injected dependencies."""
    router = APIRouter(prefix="/rag", tags=["rag"])
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

    def _resolve_document_or_raise(doc_id: str, current_user: User) -> DocumentRecord:
        try:
            return repository.get(doc_id, owner_id=current_user.id)
        except DocumentProcessingError as exc:
            detail = str(exc)
            status_code = status.HTTP_403_FORBIDDEN if "pertence" in detail.lower() else status.HTTP_404_NOT_FOUND
            raise HTTPException(status_code=status_code, detail=detail) from exc

    def _ingest_document_or_raise(doc_record: DocumentRecord) -> None:
        if not doc_record.file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo do documento não existe",
            )

        from app.domain.services.pdf_service import PDFService

        pdf_service = PDFService(logger)
        text = pdf_service.extract_text_from_pdf(str(doc_record.file_path))

        if not text or not text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Não foi possível extrair texto do documento",
            )

        rag_service.ingest_document(doc_record.doc_id, text, chunk_size=500)

    @router.post("/ask", response_model=RAGAnswerResponse)
    async def ask_question(
        payload: RAGQuestionRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> RAGAnswerResponse:
        """Ask a question about a legal document using RAG.
        
        Args:
            payload: Question payload with optional document ID
            current_user: Authenticated user
            db: Database session
            
        Returns:
            Answer with sources and jurisprudence links
        """
        try:
            if not payload.question or not payload.question.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A pergunta não pode estar vazia"
                )
            
            doc_id = payload.doc_id
            
            # If doc_id provided, verify user has access
            if doc_id:
                _resolve_document_or_raise(doc_id, current_user)
            
            # Get RAG answer
            rag_response = rag_service.answer_question(
                query=payload.question,
                doc_id=doc_id,
                system_prompt=None,
                include_sources=True
            )
            
            # Extract legal terms from question and answer
            legal_terms = jurisprudence_service.extract_jurisprudence_terms(
                document_content=rag_response["answer"],
                question=payload.question
            )
            
            # Add RAG-identified terms
            if rag_response.get("jurisprudence_terms"):
                legal_terms.extend(rag_response["jurisprudence_terms"])
            
            # Generate jurisprudence links
            jurisprudence_links = jurisprudence_service.create_jurisprudence_response(legal_terms)
            
            return RAGAnswerResponse(
                answer=rag_response["answer"],
                sources=[
                    RAGSourceChunk(
                        text=source["text"],
                        similarity=source["similarity"],
                        doc_id=source["doc_id"]
                    )
                    for source in rag_response.get("sources", [])
                ],
                legal_context=rag_response.get("legal_context"),
                jurisprudencia=[
                    JurisprudenceLink(
                        termo=link["term"],
                        url=link["url"],
                        descricao=link["description"],
                        fonte=link["source"]
                    )
                    for link in jurisprudence_links
                ]
            )
            
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error processing RAG question")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao processar pergunta"
            ) from exc

    @router.post("/ingest/{doc_id}")
    async def ingest_document(
        doc_id: str,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> dict:
        """Ingest a document into the RAG system.
        
        Args:
            doc_id: Document ID to ingest
            current_user: Authenticated user
            db: Database session
            
        Returns:
            Ingestion status
        """
        try:
            doc_record = _resolve_document_or_raise(doc_id, current_user)
            _ingest_document_or_raise(doc_record)
            
            return {
                "status": "success",
                "doc_id": doc_id,
                "message": f"Documento {doc_id} ingerido com sucesso no sistema RAG"
            }
            
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(f"Error ingesting document {doc_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao ingerir documento"
            ) from exc

    @router.post("/document/{doc_id}/ask", response_model=RAGAnswerResponse)
    async def ask_question_for_document(
        doc_id: str,
        payload: RAGDocumentQuestionRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> RAGAnswerResponse:
        """Ask a question about a specific document, auto-ingesting if needed."""
        if not payload.question or not payload.question.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A pergunta não pode estar vazia",
            )

        doc_record = _resolve_document_or_raise(doc_id, current_user)

        if payload.auto_ingest and not rag_service.store.get_chunks_by_doc_id(doc_id):
            _ingest_document_or_raise(doc_record)

        # Reuse the existing ask_question logic with the enforced doc_id
        enforced_payload = RAGQuestionRequest(question=payload.question, doc_id=doc_id)
        return await ask_question(enforced_payload, current_user=current_user, db=db)

    @router.get("/summary/{doc_id}", response_model=DocumentSummaryResponse)
    async def get_document_summary(
        doc_id: str,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> DocumentSummaryResponse:
        """Get a summary of a document.
        
        Args:
            doc_id: Document ID
            current_user: Authenticated user
            db: Database session
            
        Returns:
            Document summary with jurisprudence
        """
        try:
            doc_record = _resolve_document_or_raise(doc_id, current_user)
            
            # Get summary from RAG
            summary_data = rag_service.get_document_summary(doc_id)
            
            if "error" in summary_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=summary_data["error"]
                )
            
            # Extract legal terms from summary
            legal_terms = jurisprudence_service.extract_jurisprudence_terms(
                document_content=summary_data["summary"]
            )
            
            # Generate jurisprudence links
            jurisprudence_links = jurisprudence_service.create_jurisprudence_response(legal_terms)
            
            return DocumentSummaryResponse(
                doc_id=doc_id,
                summary=summary_data["summary"],
                chunk_count=summary_data.get("chunk_count", 0),
                jurisprudencia=[
                    JurisprudenceLink(
                        termo=link["term"],
                        url=link["url"],
                        descricao=link["description"],
                        fonte=link["source"]
                    )
                    for link in jurisprudence_links
                ]
            )
            
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(f"Error getting summary for {doc_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao gerar resumo"
            ) from exc

    return router

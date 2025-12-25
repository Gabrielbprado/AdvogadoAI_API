"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.auth_router import build_auth_router
from app.api.routers.document_router import build_document_router
from app.api.routers.rag_router import build_rag_router
from app.config.settings import Settings, get_settings
from app.domain.models.document_models import DocumentRepository
from app.domain.services.auth_service import AuthService
from app.domain.services.analysis_service import AnalysisService
from app.domain.services.user_service import UserService
from app.domain.services.pdf_service import PDFService
from app.domain.services.text_processing_service import TextProcessingService
from app.domain.services.rag_service import RAGService
from app.domain.services.jurisprudence_service import JurisprudenceService
from app.infrastructure.db.database import Base, build_session_factory, create_all
from app.infrastructure.db import entities as db_entities  # noqa: F401
from app.infrastructure.crew.agents import AgentFactory
from app.infrastructure.crew.tasks import TaskFactory
from app.infrastructure.crew.workflows import CrewWorkflow
from app.infrastructure.langgraph.graph_builder import DocumentPipelineGraph
from app.utils.file_utils import ensure_directory
from app.utils.logger import configure_logger


class ServiceContainer:
    """Centralized dependency container used for manual DI."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = configure_logger()
        ensure_directory(self.settings.storage_dir)

        self.session_factory = build_session_factory(self.settings.database_url)
        create_all(self.settings.database_url, Base, self.settings.storage_dir)

        self.repository = DocumentRepository()
        self.pdf_service = PDFService(self.logger)
        self.text_service = TextProcessingService(self.settings.max_chunk_size, self.logger)
        self.auth_service = AuthService(settings)
        self.user_service = UserService()

        llm_model = self.settings.resolve_llm_model()
        llm_base_url = self.settings.resolve_llm_base_url()
        llm_api_key = self.settings.resolve_llm_api_key()
        if self.settings.llm_provider == "openai":
            llm_identifier = llm_model
            tool_choice = None
        else:
            llm_identifier = f"{self.settings.llm_provider}/{llm_model}"
            tool_choice = "auto"

        self.agent_factory = AgentFactory(
            model=llm_identifier,
            base_url=llm_base_url,
            api_key=llm_api_key,
            tool_choice=tool_choice,
        )
        self.task_factory = TaskFactory()
        self.workflow = CrewWorkflow(self.agent_factory, self.task_factory)
        self.analysis_service = AnalysisService(self.workflow, self.logger)
        self.graph = DocumentPipelineGraph(
            repository=self.repository,
            pdf_service=self.pdf_service,
            text_service=self.text_service,
            analysis_service=self.analysis_service,
            logger=self.logger,
        )
        self.storage_dir = self.settings.storage_dir
        
        # Initialize RAG services
        openai_api_key = self.settings.openai_api_key or ""
        self.rag_service = RAGService(
            openai_api_key=openai_api_key,
            openai_model=self.settings.openai_model,
            storage_dir=self.settings.storage_dir / "rag_store",
            logger=self.logger,
        )
        self.jurisprudence_service = JurisprudenceService(logger=self.logger)


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    settings = get_settings()
    container = ServiceContainer(settings)

    application = FastAPI(title=settings.app_name)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(
        build_auth_router(
            session_factory=container.session_factory,
            auth_service=container.auth_service,
            user_service=container.user_service,
        )
    )
    application.include_router(
        build_document_router(
            repository=container.repository,
            graph=container.graph,
            storage_dir=container.storage_dir,
            session_factory=container.session_factory,
            auth_service=container.auth_service,
            user_service=container.user_service,
            jurisprudence_service=container.jurisprudence_service,
        )
    )
    application.include_router(
        build_rag_router(
            rag_service=container.rag_service,
            jurisprudence_service=container.jurisprudence_service,
            repository=container.repository,
            session_factory=container.session_factory,
            auth_service=container.auth_service,
            user_service=container.user_service,
        )
    )
    return application


app = create_app()

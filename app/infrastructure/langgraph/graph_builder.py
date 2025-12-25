"""LangGraph workflow orchestrating the end-to-end document analysis pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import List, TypedDict

from langgraph.graph import END, START, StateGraph
from logging import Logger

from app.domain.models.analysis_models import FinalAnalysisResponse
from app.domain.models.document_models import DocumentMetadata, DocumentRepository
from app.domain.services.analysis_service import AnalysisService
from app.domain.services.pdf_service import PDFService
from app.domain.services.text_processing_service import TextProcessingService


class DocumentState(TypedDict, total=False):
    """Typed state shared across LangGraph nodes."""

    doc_id: str
    file_path: Path
    metadata: DocumentMetadata
    text: str
    chunks: List[str]
    response: FinalAnalysisResponse
    user_context: str | None


class DocumentPipelineGraph:
    """Builds a LangGraph pipeline covering extraction to final response."""

    def __init__(
        self,
        *,
        repository: DocumentRepository,
        pdf_service: PDFService,
        text_service: TextProcessingService,
        analysis_service: AnalysisService,
        logger: Logger,
    ) -> None:
        self._repository = repository
        self._pdf_service = pdf_service
        self._text_service = text_service
        self._analysis_service = analysis_service
        self._logger = logger

        builder = StateGraph(DocumentState)
        builder.add_node("extract_text", self._extract_text_node)
        builder.add_node("process_text", self._process_text_node)
        builder.add_node("run_agents", self._run_agents_node)

        builder.add_edge(START, "extract_text")
        builder.add_edge("extract_text", "process_text")
        builder.add_edge("process_text", "run_agents")
        builder.add_edge("run_agents", END)

        self._graph = builder.compile()

    def run(self, doc_id: str, *, owner_id: int | None = None, user_context: str | None = None) -> FinalAnalysisResponse:
        """Execute the pipeline for a stored document, enforcing ownership when provided."""
        record = self._repository.get(doc_id, owner_id=owner_id)

        state: DocumentState = {
            "doc_id": doc_id,
            "file_path": record.file_path,
            "metadata": record.metadata,
            "user_context": user_context,
        }

        self._logger.info("Executing LangGraph pipeline for %s", doc_id)
        final_state = self._graph.invoke(state)
        return final_state["response"]

    def _extract_text_node(self, state: DocumentState) -> DocumentState:
        """Extract the text from the PDF and enrich the state."""
        extraction = self._pdf_service.extract_text(
            state["doc_id"], state["file_path"], state["metadata"]
        )
        self._logger.debug("Extraction node produced %d characters", len(extraction.text))
        state["text"] = extraction.text
        return state

    def _process_text_node(self, state: DocumentState) -> DocumentState:
        """Clean and chunk the extracted text."""
        cleaned = self._text_service.clean_text(state["text"])
        chunks = self._text_service.chunk_text(cleaned)
        state["chunks"] = chunks
        self._logger.debug("Process node produced %d chunks", len(chunks))
        return state

    def _run_agents_node(self, state: DocumentState) -> DocumentState:
        """Execute CrewAI workflow over the prepared text."""
        response = self._analysis_service.analyze(state.get("chunks", []), user_context=state.get("user_context"))
        state["response"] = response
        self._logger.debug("Run agents node completed")
        return state

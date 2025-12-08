"""Serviço responsável por orquestrar a análise via CrewAI."""
from __future__ import annotations

from typing import List, Protocol
from logging import Logger

from app.domain.models.analysis_models import FinalAnalysisResponse


class CrewWorkflowProtocol(Protocol):
    """Interface mínima esperada do workflow de IA."""

    def run(self, document_text: str) -> FinalAnalysisResponse:
        """Executa o fluxo e devolve a resposta consolidada."""
        raise NotImplementedError


class AnalysisService:
    """Limpa o texto, registra métricas e dispara o workflow."""

    def __init__(self, workflow: CrewWorkflowProtocol, logger: Logger) -> None:
        self._workflow = workflow
        self._logger = logger

    def analyze(self, chunks: List[str]) -> FinalAnalysisResponse:
        """Une os trechos e envia o conteúdo para o CrewAI."""
        document_text = "\n\n".join(chunks)
        self._logger.info("Analisando documento com %d blocos", len(chunks))
        return self._workflow.run(document_text)

"""Serviço responsável por orquestrar a análise via CrewAI."""
from __future__ import annotations

import json
from typing import List, Protocol
from logging import Logger

from app.domain.models.analysis_models import FinalAnalysisResponse, ReaderExtraction


class CrewWorkflowProtocol(Protocol):
    """Interface mínima esperada do workflow de IA."""

    def run(self, document_text: str, user_context: str | None = None) -> FinalAnalysisResponse:
        """Executa o fluxo e devolve a resposta consolidada."""
        raise NotImplementedError

    def run_reader_chunk(self, chunk_text: str, user_context: str | None = None) -> ReaderExtraction:
        """Executa o agente leitor em um trecho do documento."""
        raise NotImplementedError

    def run_final_analysis(
        self, aggregated_context: str, user_context: str | None = None
    ) -> FinalAnalysisResponse:
        """Executa a análise final com base no contexto agregado."""
        raise NotImplementedError


class AnalysisService:
    """Limpa o texto, registra métricas e dispara o workflow."""

    def __init__(self, workflow: CrewWorkflowProtocol, logger: Logger) -> None:
        self._workflow = workflow
        self._logger = logger

    def analyze(self, chunks: List[str], user_context: str | None = None) -> FinalAnalysisResponse:
        """Processa os chunks em paralelo (simulado) e agrega os resultados."""
        self._logger.info("Iniciando análise map-reduce com %d blocos", len(chunks))
        
        # 1. Map Step: Process each chunk with Reader Agent
        reader_results: List[ReaderExtraction] = []
        for i, chunk in enumerate(chunks):
            self._logger.debug("Processando chunk %d/%d", i + 1, len(chunks))
            try:
                result = self._workflow.run_reader_chunk(chunk, user_context)
                reader_results.append(result)
            except Exception as exc:
                self._logger.error("Erro ao processar chunk %d: %s", i + 1, exc)
                # Continue processing other chunks even if one fails
                continue

        if not reader_results:
            raise ValueError("Falha ao extrair informações de todos os blocos do documento.")

        # 2. Reduce Step: Aggregate results
        aggregated_extraction = self._aggregate_extractions(reader_results)
        
        # 3. Prepare context for Analyst/Writer
        aggregated_context = self._format_extraction_for_context(aggregated_extraction)
        
        # 4. Final Analysis Step
        final_response = self._workflow.run_final_analysis(aggregated_context, user_context)
        
        # Inject the full aggregated extraction into the final response
        final_response.extracao = aggregated_extraction
        
        return final_response

    def _aggregate_extractions(self, results: List[ReaderExtraction]) -> ReaderExtraction:
        """Combina os resultados parciais em um único objeto de extração."""
        aggregated = ReaderExtraction()
        
        for res in results:
            aggregated.topicos_principais.extend(res.topicos_principais)
            aggregated.clausulas.extend(res.clausulas)
            aggregated.pontos_chave.extend(res.pontos_chave)
            
            # Merge nested structures
            aggregated.informacoes_extraidas.partes.extend(res.informacoes_extraidas.partes)
            aggregated.informacoes_extraidas.valores.extend(res.informacoes_extraidas.valores)
            aggregated.informacoes_extraidas.datas.extend(res.informacoes_extraidas.datas)
            
        # TODO: Implementar deduplicação inteligente aqui se necessário
        return aggregated

    def _format_extraction_for_context(self, extraction: ReaderExtraction) -> str:
        """Converte a extração estruturada em texto para o prompt do analista."""
        return json.dumps(extraction.model_dump(), indent=2, ensure_ascii=False)

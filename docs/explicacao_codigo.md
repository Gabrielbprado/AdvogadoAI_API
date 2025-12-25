# LawerAI — Visão Geral e Passo a Passo do Código

Este documento descreve o objetivo do projeto, a arquitetura, o fluxo de ponta a ponta e comenta linha a linha (ou bloco a bloco imediato) de cada arquivo principal. Use-o como guia de estudo.

## Objetivo da aplicação
- Fornecer uma API FastAPI que recebe PDFs, extrai texto, segmenta em blocos, aciona um pipeline LangGraph que orquestra serviços de PDF e NLP, e executa um fluxo CrewAI de agentes (Leitor, Analista, Redator) para devolver uma análise jurídica estruturada.

## Fluxo alto nível (request → resposta)
1. `POST /document/upload`: recebe o PDF, salva no disco (`data/uploads`) e registra o metadado no repositório em memória.
2. `POST /document/analyze/{doc_id}`: busca o registro, roda o grafo `DocumentPipelineGraph`:
   - Extrai texto do PDF (`PDFService`).
   - Limpa e quebra em chunks (`TextProcessingService`).
   - Dispara análise map-reduce (`AnalysisService` + `CrewWorkflow`), agregando extrações e gerando parecer final.
3. Devolve `FinalAnalysisResponse` com extração, análise e parecer.

## Arquitetura e camadas
- **API**: roteadores FastAPI (`document_router.py`).
- **Config**: `settings.py` carrega env vars e resolve modelo LLM.
- **Domínio**: modelos Pydantic para documentos e análises; serviços `PDFService`, `TextProcessingService`, `AnalysisService`.
- **Infra**: integração com CrewAI (`agents.py`, `tasks.py`, `workflows.py`) e LangGraph (`graph_builder.py`).
- **Utilitários**: arquivos e logging (`file_utils.py`, `logger.py`).
- **DI manual**: `ServiceContainer` em `main.py` instancia dependências e injeta no roteador.

## Fluxo detalhado entre funções e arquivos
1. `main.py#create_app` monta `ServiceContainer`, configura CORS e inclui o roteador de documentos.
2. `document_router.build_document_router` expõe `/upload` (gera `doc_id`, salva arquivo, registra metadado) e `/analyze/{doc_id}` (chama `DocumentPipelineGraph.run`).
3. `DocumentPipelineGraph.run` consulta `DocumentRepository`, executa nós em ordem:
   - `_extract_text_node` → `PDFService.extract_text` abre PDF (pdfplumber) e concatena páginas.
   - `_process_text_node` → `TextProcessingService.clean_text` e `chunk_text` criam blocos.
   - `_run_agents_node` → `AnalysisService.analyze` roda map-reduce em CrewAI.
4. `AnalysisService.analyze`:
   - Loop de chunks chama `CrewWorkflow.run_reader_chunk` (agente Leitor) e acumula `ReaderExtraction`.
   - `_aggregate_extractions` mescla tópicos, cláusulas e entidades.
   - `_format_extraction_for_context` serializa JSON para contexto.
   - `CrewWorkflow.run_final_analysis` (Analista + Redator) gera `FinalAnalysisResponse` e injeta a extração agregada.
5. `CrewWorkflow` cria agentes via `AgentFactory` e tarefas via `TaskFactory`, aciona `Crew.kickoff` e faz parsing robusto com `parse_task_output` (normalizações, fallback de JSON).

## Comentário linha a linha (principais arquivos)

### `app/main.py`
## Comentário linha a linha (principais arquivos)

Ordem por dependência: configuração → utilitários → modelos → serviços de domínio → infraestrutura CrewAI → LangGraph → API → aplicação (`main` por último).

### `app/config/settings.py`
```python
"""Application settings and configuration helpers."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
   """Strongly typed settings loaded from the environment or .env files."""

   app_name: str = Field(default="LawerAI")
   environment: str = Field(default="development")
   storage_dir: Path = Field(default=Path("data/uploads"))
   llm_provider: Literal["openai", "gemini", "groq", "ollama"] = Field(default="openai")
   crewai_model: Optional[str] = Field(default=None)
   openai_model: str = Field(default="gpt-4o-mini")
   gemini_model: str = Field(default="gemini-1.5-pro")
   groq_model: str = Field(default="llama3-70b-8192")
   ollama_model: str = Field(default="llama3")
   ollama_base_url: Optional[str] = Field(default="http://localhost:11434")
   openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
   google_api_key: Optional[str] = Field(default=None, validation_alias="GOOGLE_API_KEY")
   groq_api_key: Optional[str] = Field(default=None, validation_alias="GROQ_API_KEY")
   crewai_log_level: Optional[str] = Field(default=None, validation_alias="CREWAI_LOG_LEVEL")
   crewai_logging_level: Optional[str] = Field(default=None, validation_alias="CREWAI_LOGGING_LEVEL")
   max_chunk_size: int = Field(default=2000, ge=256)
   langgraph_concurrency: int = Field(default=1, ge=1)
   cors_allowed_origins: List[str] = Field(
      default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
      validation_alias="CORS_ALLOWED_ORIGINS",
   )

   model_config = SettingsConfigDict(env_file=".env", env_prefix="LAWERAI_", case_sensitive=False)

   def resolve_llm_model(self) -> str:
      """Return the concrete model to be used by CrewAI based on provider preferences."""
      if self.crewai_model:
         return self.crewai_model
      provider_defaults = {
         "openai": self.openai_model,
         "gemini": self.gemini_model,
         "groq": self.groq_model,
         "ollama": self.ollama_model,
      }
      return provider_defaults[self.llm_provider]

   def resolve_llm_base_url(self) -> Optional[str]:
      """Return provider specific base URL overrides when needed."""
      if self.llm_provider == "ollama":
         return self.ollama_base_url
      return None

   def resolve_llm_api_key(self) -> Optional[str]:
      """Return provider specific API key when available."""
      if self.llm_provider == "openai":
         return self.openai_api_key
      if self.llm_provider == "gemini":
         return self.google_api_key
      if self.llm_provider == "groq":
         return self.groq_api_key
      return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
   """Return a cached settings instance."""
   return Settings()
```
- 1: docstring e imports.
- 9-27: campos configuráveis (app, ambiente, storage, LLMs, chaves, chunk size, CORS).
- 29: `model_config` define .env e prefixo `LAWERAI_`.
- 31-45: resoluções de modelo/base URL/API key por provider.
- 48-52: `get_settings` em cache.

### `app/utils/logger.py`
```python
"""Application wide logging utilities."""
from __future__ import annotations

import logging
from logging import Logger
from typing import Optional

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logger(name: str = "lawerai", level: int = logging.INFO) -> Logger:
   """Configure and return a structured logger for the application."""
   logger = logging.getLogger(name)
   if not logger.handlers:
      handler = logging.StreamHandler()
      handler.setFormatter(logging.Formatter(_LOG_FORMAT))
      logger.addHandler(handler)
   logger.setLevel(level)
   logger.propagate = False
   return logger


def get_logger(name: Optional[str] = None) -> Logger:
   """Retrieve a configured logger, defaulting to the root application logger."""
   return configure_logger(name or "lawerai")
```
- Configuração simples de logger com formatação padronizada.

### `app/utils/file_utils.py`
```python
"""Utility helpers for handling files and uploads."""
from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile


def ensure_directory(path: Path) -> Path:
   """Ensure the directory exists and return it."""
   path.mkdir(parents=True, exist_ok=True)
   return path


def generate_document_id(prefix: str = "doc") -> str:
   """Generate a unique document identifier."""
   return f"{prefix}-{uuid4()}"


def save_upload_file(upload_file: UploadFile, destination_dir: Path, *, filename: Optional[str] = None) -> Path:
   """Persist an uploaded file to disk and return the absolute path."""
   ensure_directory(destination_dir)
   resolved_name = filename or upload_file.filename or generate_document_id("upload")
   destination = destination_dir / resolved_name
   with destination.open("wb") as buffer:
      contents = upload_file.file.read()
      buffer.write(contents)
   upload_file.file.close()
   return destination


def read_file_bytes(file_path: Path) -> bytes:
   """Read a file and return its content as bytes."""
   return file_path.read_bytes()
```
- Funções utilitárias completas para diretórios, IDs e upload.

### `app/domain/models/document_models.py`
```python
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

   def get(self, doc_id: str) -> DocumentRecord:
      """Retrieve a document record or raise an error if absent."""
      try:
         return self._records[doc_id]
      except KeyError as exc:
         raise DocumentProcessingError(f"Document {doc_id} not found") from exc

   def exists(self, doc_id: str) -> bool:
      """Return whether a document record exists."""
      return doc_id in self._records
```
- 1-6: imports e exceção customizada.
- 8-16: `DocumentMetadata`.
- 18-28: `DocumentRecord` com Path permitido.
- 30-35: `DocumentUploadResponse`.
- 37-43: `DocumentExtractionResult`.
- 45-60: repositório in-memory com `save/get/exists` e erro 404.

### `app/domain/models/analysis_models.py`
```python
"""Structured models for agent-driven analysis outputs."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Clausula(BaseModel):
   """Cláusula extraída do documento."""

   model_config = ConfigDict(extra="ignore")

   numero: Optional[str] = None
   titulo: str = Field(default="", description="Título da cláusula (ex: 'DO OBJETO')")
   texto: str = Field(default="", description="Texto integral da cláusula")


class ParteInfo(BaseModel):
   """Informações estruturadas das partes."""

   model_config = ConfigDict(extra="ignore")

   tipo: Optional[str] = None
   nome: str = ""
   cnpj: Optional[str] = None
   endereco: Optional[str] = None


class ValorInfo(BaseModel):
   """Valores monetários relevantes."""

   model_config = ConfigDict(extra="ignore")

   descricao: str = ""
   valor: Optional[str] = None


class DataInfo(BaseModel):
   """Datas e prazos mencionados no documento."""

   model_config = ConfigDict(extra="ignore")

   descricao: str = ""
   data: Optional[str] = None
   prazo: Optional[str] = None
   valor: Optional[str] = None


class InformacoesExtraidas(BaseModel):
   """Detalhamento estruturado retornado pelo agente leitor."""

   model_config = ConfigDict(extra="ignore")

   partes: List[ParteInfo] = Field(default_factory=list)
   valores: List[ValorInfo] = Field(default_factory=list)
   datas: List[DataInfo] = Field(default_factory=list)


class ReaderExtraction(BaseModel):
   """Esquema do resultado do agente Leitor."""

   model_config = ConfigDict(extra="ignore")

   topicos_principais: List[str] = Field(default_factory=list)
   clausulas: List[Clausula] = Field(default_factory=list)
   pontos_chave: List[str] = Field(default_factory=list)
   informacoes_extraidas: InformacoesExtraidas = Field(default_factory=InformacoesExtraidas)


class AnalystEvaluation(BaseModel):
   """Esquema do resultado do agente Analista."""

   model_config = ConfigDict(extra="ignore")

   riscos: List[str] = Field(default_factory=list)
   inconsistencias: List[str] = Field(default_factory=list)
   clausulas_abusivas: List[str] = Field(default_factory=list)
   melhorias_recomendadas: List[str] = Field(default_factory=list)


class ContraProposta(BaseModel):
   """Sugestões estruturadas do agente redator."""

   model_config = ConfigDict(extra="ignore")

   clausula_vigencia: Optional[str] = None
   clausula_multa: Optional[str] = None
   clausula_obrigacoes: Optional[str] = None
   clausula_resolucao_conflitos: Optional[str] = None


class LawyerDraft(BaseModel):
   """Esquema do resultado do agente Redator."""

   model_config = ConfigDict(extra="ignore")

   parecer_resumido: str = ""
   parecer_detalhado: str = ""
   contra_proposta: ContraProposta = Field(default_factory=ContraProposta)


class FinalAnalysisResponse(BaseModel):
   """Resposta completa devolvida pela API."""

   extracao: ReaderExtraction
   analise: AnalystEvaluation
   parecer: LawyerDraft
```
- 1-7: imports e config.
- 9-28: `Clausula` com extras ignorados.
- 30-43: `ParteInfo`.
- 45-55: `ValorInfo`.
- 57-70: `DataInfo`.
- 72-80: `InformacoesExtraidas` lista entidades.
- 82-93: `ReaderExtraction` campos do leitor.
- 95-104: `AnalystEvaluation` campos do analista.
- 106-118: `ContraProposta` do redator.
- 120-132: `LawyerDraft`.
- 134-139: `FinalAnalysisResponse` agrega tudo.

### `app/domain/services/pdf_service.py`
```python
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
```
- 1-12: imports.
- 15-17: construtor com logger.
- 19-34: `extract_text` abre pdfplumber, concatena texto, valida vazio, loga e retorna `DocumentExtractionResult`.

### `app/domain/services/text_processing_service.py`
```python
"""Domain service for text normalization and chunking."""
from __future__ import annotations

import re
from typing import List
from logging import Logger


class TextProcessingService:
   """Provides utilities to sanitize and chunk extracted text."""

   def __init__(self, max_chunk_size: int, logger: Logger) -> None:
      self._max_chunk_size = max_chunk_size
      self._logger = logger

   def clean_text(self, text: str) -> str:
      """Normalize whitespace and remove non-printable characters."""
      normalized = re.sub(r"\s+", " ", text).strip()
      self._logger.debug("Normalized text length: %d", len(normalized))
      return normalized

   def chunk_text(self, text: str) -> List[str]:
      """Split text into manageable chunks for model consumption."""
      if not text:
         return []
      chunks = [
         text[i : i + self._max_chunk_size]
         for i in range(0, len(text), self._max_chunk_size)
      ]
      self._logger.debug("Generated %d chunks", len(chunks))
      return chunks
```
- 1-8: imports.
- 11-15: construtor armazena config e logger.
- 17-23: `clean_text` normaliza espaços e loga.
- 25-35: `chunk_text` fatia texto e loga quantidade.

### `app/domain/services/analysis_service.py`
```python
"""Serviço responsável por orquestrar a análise via CrewAI."""
from __future__ import annotations

import json
from typing import List, Protocol
from logging import Logger

from app.domain.models.analysis_models import FinalAnalysisResponse, ReaderExtraction


class CrewWorkflowProtocol(Protocol):
   """Interface mínima esperada do workflow de IA."""

   def run(self, document_text: str) -> FinalAnalysisResponse:
      """Executa o fluxo e devolve a resposta consolidada."""
      raise NotImplementedError

   def run_reader_chunk(self, chunk_text: str) -> ReaderExtraction:
      """Executa o agente leitor em um trecho do documento."""
      raise NotImplementedError

   def run_final_analysis(self, aggregated_context: str) -> FinalAnalysisResponse:
      """Executa a análise final com base no contexto agregado."""
      raise NotImplementedError


class AnalysisService:
   """Limpa o texto, registra métricas e dispara o workflow."""

   def __init__(self, workflow: CrewWorkflowProtocol, logger: Logger) -> None:
      self._workflow = workflow
      self._logger = logger

   def analyze(self, chunks: List[str]) -> FinalAnalysisResponse:
      """Processa os chunks em paralelo (simulado) e agrega os resultados."""
      self._logger.info("Iniciando análise map-reduce com %d blocos", len(chunks))
        
      # 1. Map Step: Process each chunk with Reader Agent
      reader_results: List[ReaderExtraction] = []
      for i, chunk in enumerate(chunks):
         self._logger.debug("Processando chunk %d/%d", i + 1, len(chunks))
         try:
            result = self._workflow.run_reader_chunk(chunk)
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
      final_response = self._workflow.run_final_analysis(aggregated_context)
        
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
```
- 1-9: imports e protocolo do workflow.
- 11-26: interface com métodos esperados.
- 28-74: `AnalysisService.analyze` faz map-reduce, lida com erros por chunk, agrega, formata contexto e chama final analysis.
- 76-95: `_aggregate_extractions` mescla listas e informa TODO de deduplicação.
- 97-99: `_format_extraction_for_context` serializa JSON.

### `app/infrastructure/crew/agents.py`
```python
"""CrewAI agent factory definitions."""
from __future__ import annotations

from typing import Optional

from crewai import Agent, LLM

_PT_DIRECTIVE = "Produza respostas objetivas em portugues brasileiro formal e mantenha dados estruturados quando solicitados."


class AgentFactory:
   """Factory responsible for instantiating CrewAI agents."""

   def __init__(
      self,
      *,
      model: str,
      base_url: Optional[str] = None,
      api_key: Optional[str] = None,
      tool_choice: Optional[str] = None,
   ) -> None:
      llm_kwargs = {"model": model}
      if base_url:
         llm_kwargs["base_url"] = base_url
      if api_key:
         llm_kwargs["api_key"] = api_key
      if tool_choice:
         llm_kwargs["tool_choice"] = tool_choice
      self._llm = LLM(**llm_kwargs)

   def _base_agent(self, role: str, goal: str, backstory: str) -> Agent:
      return Agent(
         role=role,
         goal=f"{goal} {_PT_DIRECTIVE}",
         backstory=backstory,
         llm=self._llm,
         verbose=True,
         allow_delegation=False,
      )

   def create_reader(self) -> Agent:
      """Create the Reader (Leitor Jurídico) agent."""
      return self._base_agent(
         role="Leitor Jurídico",
         goal="Extrair topicos principais, clausulas, partes, datas e valores",
         backstory=(
            "Especialista em contratos que resume documentos extensos e identifica obrigações críticas."
         ),
      )

   def create_analyst(self) -> Agent:
      """Create the Analyst (Analista Jurídico) agent."""
      return self._base_agent(
         role="Analista Jurídico",
         goal="Mapear riscos, inconsistências e sugerir melhorias acionáveis",
         backstory="Advogado corporativo focado em compliance e mitigacao de passivos.",
      )

   def create_writer(self) -> Agent:
      """Create the Lawyer Writer (Redator Jurídico) agent."""
      return self._base_agent(
         role="Redator Jurídico",
         goal="Produzir parecer profissional completo e contra-proposta",
         backstory="Redator juridico experiente que consolida todo o estudo em linguagem tecnica e clara.",
      )
```
- 1-8: imports e diretiva PT.
- 10-28: construtor monta LLM com base_url/api_key/tool_choice.
- 30-37: `_base_agent` aplica diretiva e configura Agent.
- 39-63: `create_reader/analyst/writer` com roles/objetivos/backstories.

### `app/infrastructure/crew/tasks.py`
```python
"""CrewAI task definitions and helpers."""
from __future__ import annotations

import ast
import json
import re
from typing import Any, List, Type, TypeVar

from crewai import Agent, Task
from pydantic import BaseModel, ValidationError

from app.utils.logger import get_logger
logger = get_logger(__name__)


TModel = TypeVar("TModel", bound=BaseModel)

READER_EXPECTED_JSON = {
   "topicos_principais": [],
   "clausulas": [
      {"numero": "1", "titulo": "DO OBJETO", "texto": "O presente contrato tem como objeto..."}
   ],
   "pontos_chave": [],
   "informacoes_extraidas": {"partes": [], "valores": [], "datas": []},
}

ANALYST_EXPECTED_JSON = {
   "riscos": [],
   "inconsistencias": [],
   "clausulas_abusivas": [],
   "melhorias_recomendadas": [],
}

LAWYER_EXPECTED_JSON = {
   "parecer_resumido": "",
   "parecer_detalhado": "",
   "contra_proposta": "",
}

_PT_JSON_DIRECTIVE = (
   "Use apenas portugues brasileiro formal e devolva JSON valido exatamente no formato esperado."
)


class TaskFactory:
   """Factory for strongly typed CrewAI tasks."""

   def _build_task(self, agent: Agent, prompt: str, expected: dict) -> Task:
      full_description = f"{prompt}\n\n{_PT_JSON_DIRECTIVE}"
      return Task(
         description=full_description,
         expected_output=json.dumps(expected, ensure_ascii=False),
         agent=agent,
      )

   def create_reader_task(self, agent: Agent) -> Task:
      prompt = (
         "Analise o trecho do contrato e extraia TODAS as cláusulas presentes nele. "
         "Se houver cláusulas numeradas (1, 2, 3...), capture o número, o título e o texto completo. "
         "Não resuma o texto da cláusula. "
         "Também extraia tópicos principais, partes, valores e datas."
      )
      return self._build_task(agent, prompt, READER_EXPECTED_JSON)

   def create_analyst_task(self, agent: Agent) -> Task:
      prompt = (
         "A partir da extracao do leitor, detalhe riscos juridicos, inconsistencias, clausulas abusivas "
         "e melhorias recomendadas."
      )
      return self._build_task(agent, prompt, ANALYST_EXPECTED_JSON)

   def create_writer_task(self, agent: Agent) -> Task:
      prompt = (
         "Consolide todo o estudo em parecer resumido, parecer detalhado e contra-proposta juridica."
      )
      return self._build_task(agent, prompt, LAWYER_EXPECTED_JSON)


def parse_task_output(content: str, model: Type[TModel]) -> TModel:
   """Parse a JSON string coming from CrewAI into a Pydantic model."""
   cleaned = _extract_json_blob(content)
   normalized = cleaned.replace("“", '"').replace("”", '"')
   try:
      payload = _parse_with_fallback(normalized)
   except ValueError:
      payload = {}
   payload = _normalize_payload(payload, model)
   try:
      return model.model_validate(payload)
   except ValidationError:
      logger.warning(
         "Falha ao validar resposta do agente %s. Retornando defaults. Conteudo parcial: %s",
         model.__name__,
         cleaned[:200],
      )
      return model()


def _extract_json_blob(raw: str) -> str:
   """Attempt to isolate a JSON object even if wrapped in prose or fences."""
   candidate = raw.strip()
   if "```" in candidate:
      blocks = re.findall(r"```[a-zA-Z0-9_-]*\s*(.*?)```", candidate, flags=re.DOTALL)
      if blocks:
         candidate = blocks[-1].strip()
   start = candidate.find("{")
   end = candidate.rfind("}")
   if start != -1 and end != -1 and end > start:
      return candidate[start : end + 1]
   return candidate


def _parse_with_fallback(serialized: str) -> dict | list:
   """Try strict JSON parsing, falling back to literal eval when needed."""
   try:
      return json.loads(serialized)
   except json.JSONDecodeError:
      repaired = _repair_common_json_issues(serialized)
      try:
         return json.loads(repaired)
      except json.JSONDecodeError:
         serialized = repaired
      try:
         evaluated = ast.literal_eval(serialized)
      except (ValueError, SyntaxError) as exc:
         raise ValueError("Nao foi possivel interpretar a resposta como JSON valido") from exc
      if isinstance(evaluated, (dict, list)):
         return evaluated
      raise ValueError("Resposta nao estruturada")


def _repair_common_json_issues(payload: str) -> str:
   """Best-effort cleanup for trailing commas and missing braces."""
   repaired = payload
   repaired = re.sub(r",\s*(\}|\])", r"\1", repaired)
   brace_delta = repaired.count("{") - repaired.count("}")
   bracket_delta = repaired.count("[") - repaired.count("]")
   if brace_delta > 0:
      repaired += "}" * brace_delta
   if bracket_delta > 0:
      repaired += "]" * bracket_delta
   return repaired


def _normalize_payload(payload: Any, model: Type[TModel]) -> Any:
   """Coerce arbitrary agent output into the expected schema."""
   name = model.__name__
   if name == "ReaderExtraction":
      return _normalize_reader_payload(payload)
   if name == "AnalystEvaluation":
      return _normalize_analyst_payload(payload)
   if name == "LawyerDraft":
      return _normalize_lawyer_payload(payload)
   return payload


def _normalize_reader_payload(payload: Any) -> dict:
   data = _ensure_dict(payload)
   data["topicos_principais"] = _coerce_list_of_strings(data.get("topicos_principais"))
   data["pontos_chave"] = _coerce_list_of_strings(data.get("pontos_chave"))
   data["clausulas_relevantes"] = _coerce_clause_list(data.get("clausulas_relevantes"))

   info = _ensure_dict(data.get("informacoes_extraidas"))
   info["partes"] = _coerce_entities(info.get("partes"), ["tipo", "nome", "cnpj", "endereco"], "descricao")
   info["valores"] = _coerce_entities(info.get("valores"), ["descricao", "valor"], "descricao")
   info["datas"] = _coerce_entities(info.get("datas"), ["descricao", "data", "prazo", "valor"], "descricao")
   data["informacoes_extraidas"] = info
   return data


def _normalize_analyst_payload(payload: Any) -> dict:
   data = _ensure_dict(payload)
   for field in ["riscos", "inconsistencias", "clausulas_abusivas", "melhorias_recomendadas"]:
      data[field] = _coerce_list_of_strings(data.get(field))
   return data


def _normalize_lawyer_payload(payload: Any) -> dict:
   data = _ensure_dict(payload)
   data["parecer_resumido"] = _coerce_string(data.get("parecer_resumido"))
   data["parecer_detalhado"] = _coerce_string(data.get("parecer_detalhado"))
   contra = _ensure_dict(data.get("contra_proposta"))
   for key in ["clausula_vigencia", "clausula_multa", "clausula_obrigacoes", "clausula_resolucao_conflitos"]:
      contra[key] = _coerce_string(contra.get(key))
   data["contra_proposta"] = contra
   return data


def _coerce_list_of_strings(value: Any) -> List[str]:
   if value is None:
      return []
   if isinstance(value, str):
      text = value.strip()
      return [text] if text else []
   if isinstance(value, list):
      result: List[str] = []
      for item in value:
         if isinstance(item, str):
            text = item.strip()
            if text:
               result.append(text)
         elif isinstance(item, dict):
            text = ", ".join(str(v).strip() for v in item.values() if v)
            if text:
               result.append(text)
      return result
   if isinstance(value, dict):
      text = ", ".join(f"{k}: {v}" for k, v in value.items() if v)
      return [text] if text else []
   return [str(value)]


def _coerce_clause_list(value: Any) -> List[dict]:
   if not value:
      return []
   items = value if isinstance(value, list) else [value]
   clauses: List[dict] = []
   for item in items:
      if isinstance(item, dict):
         clauses.append(
            {
               "numero": _coerce_string(item.get("numero")),
               "descricao": _coerce_string(item.get("descricao") or item.get("titulo") or item.get("clausula")),
               "detalhes": _coerce_string(item.get("detalhes") or item.get("descricao") or item.get("texto")),
            }
         )
      else:
         text = _coerce_string(item)
         if text:
            clauses.append({"descricao": text})
   return clauses


def _coerce_entities(value: Any, allowed_keys: List[str], fallback_key: str) -> List[dict]:
   if not value:
      return []
   items = value if isinstance(value, list) else [value]
   entities: List[dict] = []
   for item in items:
      if isinstance(item, dict):
         entity = {key: _coerce_string(item.get(key)) for key in allowed_keys}
         if any(entity.values()):
            entities.append(entity)
      else:
         text = _coerce_string(item)
         if text:
            entities.append({fallback_key: text})
   return entities


def _coerce_string(value: Any) -> str:
   if value is None:
      return ""
   if isinstance(value, (int, float)):
      return str(value)
   return str(value).strip()


def _ensure_dict(value: Any) -> dict:
   if isinstance(value, dict):
      return dict(value)
   return {}
```
- Código completo com prompts, criação de tasks e parsing robusto.
- Observe `parse_task_output` que faz limpeza, parse com fallback e normalização por modelo.

### `app/infrastructure/crew/workflows.py`
```python
"""CrewAI workflow orchestration helpers."""
from __future__ import annotations

from typing import Any, List

from crewai import Crew, Process

from app.domain.models.analysis_models import AnalystEvaluation, FinalAnalysisResponse, LawyerDraft, ReaderExtraction
from app.infrastructure.crew.agents import AgentFactory
from app.infrastructure.crew.tasks import TaskFactory, parse_task_output
from app.utils.logger import get_logger


class CrewWorkflow:
   """Builds and executes the CrewAI workflow for document analysis."""

   def __init__(self, agent_factory: AgentFactory, task_factory: TaskFactory) -> None:
      self._agent_factory = agent_factory
      self._task_factory = task_factory
      self._logger = get_logger(__name__)

   def run(self, document_text: str) -> FinalAnalysisResponse:
      """Execute the CrewAI crew sequentially and parse the outputs."""
      # Legacy method, kept for compatibility or full-text runs
      reader_agent = self._agent_factory.create_reader()
      analyst_agent = self._agent_factory.create_analyst()
      writer_agent = self._agent_factory.create_writer()

      reader_task = self._task_factory.create_reader_task(reader_agent)
      analyst_task = self._task_factory.create_analyst_task(analyst_agent)
      writer_task = self._task_factory.create_writer_task(writer_agent)

      reader_task.description = (
         f"{reader_task.description}\n\nDocumento para análise:\n{document_text}"
      )

      crew = Crew(
         agents=[reader_agent, analyst_agent, writer_agent],
         tasks=[reader_task, analyst_task, writer_task],
         process=Process.sequential,
         verbose=True,
      )

      raw_result = crew.kickoff(inputs={"document_text": document_text})
      responses = self._resolve_task_outputs(raw_result)
      self._logger.debug("Respostas do Crew: %s", responses)

      reader_output = parse_task_output(responses[0], ReaderExtraction)
      analyst_output = parse_task_output(responses[1], AnalystEvaluation)
      writer_output = parse_task_output(responses[2], LawyerDraft)
      return FinalAnalysisResponse(
         extracao=reader_output,
         analise=analyst_output,
         parecer=writer_output,
      )

   def run_reader_chunk(self, chunk_text: str) -> ReaderExtraction:
      """Run only the Reader agent on a specific text chunk."""
      reader_agent = self._agent_factory.create_reader()
      reader_task = self._task_factory.create_reader_task(reader_agent)
        
      # Append chunk to the existing description to preserve instructions and JSON directive
      reader_task.description = (
         f"{reader_task.description}\n\nTrecho do documento para análise:\n{chunk_text}"
      )

      crew = Crew(
         agents=[reader_agent],
         tasks=[reader_task],
         process=Process.sequential,
         verbose=False, # Less verbose for chunks
      )

      raw_result = crew.kickoff()
      responses = self._resolve_task_outputs(raw_result)
      return parse_task_output(responses[0], ReaderExtraction)

   def run_final_analysis(self, aggregated_context: str) -> FinalAnalysisResponse:
      """Run Analyst and Writer on the aggregated context from all chunks."""
      analyst_agent = self._agent_factory.create_analyst()
      writer_agent = self._agent_factory.create_writer()

      analyst_task = self._task_factory.create_analyst_task(analyst_agent)
      writer_task = self._task_factory.create_writer_task(writer_agent)

      # Inject aggregated context into Analyst task
      analyst_task.description = (
         f"{analyst_task.description}\n\nContexto consolidado do documento:\n{aggregated_context}"
      )

      crew = Crew(
         agents=[analyst_agent, writer_agent],
         tasks=[analyst_task, writer_task],
         process=Process.sequential,
         verbose=True,
      )

      raw_result = crew.kickoff()
      responses = self._resolve_task_outputs(raw_result)
        
      # responses[0] is Analyst, responses[1] is Writer
      analyst_output = parse_task_output(responses[0], AnalystEvaluation)
      writer_output = parse_task_output(responses[1], LawyerDraft)
        
      # We construct a dummy ReaderExtraction because we don't have a single one anymore, 
      # or we could try to parse the aggregated context back if it was a JSON.
      # For now, return empty or partial.
      # Ideally, we should pass the aggregated reader extraction here if we want it in the final response.
      # But FinalAnalysisResponse requires it.
        
      return FinalAnalysisResponse(
         extracao=ReaderExtraction(), # Placeholder, or we need to pass it in
         analise=analyst_output,
         parecer=writer_output,
      )

   def _resolve_task_outputs(self, raw_result: Any) -> List[str]:
      """Normalize CrewAI outputs into raw strings per task."""
      outputs: List[str] = []
      task_outputs = getattr(raw_result, "tasks_output", raw_result)
      iterable = task_outputs if isinstance(task_outputs, list) else [task_outputs]
      for item in iterable:
         if isinstance(item, dict):
            outputs.append(str(item.get("raw", item.get("output", ""))))
         elif hasattr(item, "raw"):
            outputs.append(str(getattr(item, "raw")))
         else:
            outputs.append(str(item))
      while len(outputs) < 3:
         outputs.append("{}")
      return outputs
```
- Código completo com três modos (full-text, chunk e final) e parsing.
- Atenção ao placeholder `ReaderExtraction()` em `run_final_analysis`.

### `app/infrastructure/langgraph/graph_builder.py`
```python
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

   def run(self, doc_id: str) -> FinalAnalysisResponse:
      """Execute the pipeline for a stored document."""
      record = self._repository.get(doc_id)
        
      state: DocumentState = {
         "doc_id": doc_id,
         "file_path": record.file_path,
         "metadata": record.metadata,
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
      response = self._analysis_service.analyze(state.get("chunks", []))
      state["response"] = response
      self._logger.debug("Run agents node completed")
      return state
```
- 1-12: imports LangGraph, logger, modelos e serviços.
- 14-23: `DocumentState` define campos no estado.
- 25-61: construtor recebe dependências, monta grafo com nós e arestas.
- 63-72: `run` busca registro, prepara estado e invoca grafo.
- 74-82: `_extract_text_node` extrai texto via PDFService.
- 84-91: `_process_text_node` limpa e chunk.
- 93-99: `_run_agents_node` chama AnalysisService e armazena resposta.

### `app/api/routers/document_router.py`
```python
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
```
- 1-14: imports.
- 16-24: função recebe repo/grafo/storage e cria router.
- 27-40: `/upload` gera `doc_id`, salva PDF, monta metadados e guarda no repo.
- 42-55: `/analyze/{doc_id}` roda grafo e trata erros 404/502/500.

### `app/main.py`
```python
"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.document_router import build_document_router
from app.config.settings import Settings, get_settings
from app.domain.models.document_models import DocumentRepository
from app.domain.services.analysis_service import AnalysisService
from app.domain.services.pdf_service import PDFService
from app.domain.services.text_processing_service import TextProcessingService
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

      self.repository = DocumentRepository()
      self.pdf_service = PDFService(self.logger)
      self.text_service = TextProcessingService(self.settings.max_chunk_size, self.logger)

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
      build_document_router(
         repository=container.repository,
         graph=container.graph,
         storage_dir=container.storage_dir,
      )
   )
   return application


app = create_app()
```
- Linha 1: docstring.
- 4-14: imports de FastAPI, CORS, rotas, settings, serviços e utils.
- 17-44: `ServiceContainer` monta logger, diretório, repo, serviços de PDF/texto, resolve modelo/URL/API key e tool_choice.
- 46-57: cria factories/tarefas/workflow/analysis_service/grafo e guarda storage_dir.
- 60-80: `create_app` instancia settings/container, cria FastAPI, adiciona CORS e router com dependências.
- 83: cria instância global `app`.

### Sobre `business_router.py`
- Existe router para `/business`, mas o arquivo `domain/models/business_models.py` referenciado não está no projeto; rotas usarão um repositório inexistente e falharão se incluídas. Atualmente `main.py` não inclui esse router, então permanece inativo.

## Possíveis pontos de atenção
- `DocumentRepository` é in-memory: reiniciar a aplicação perde uploads; considere persistência real.
- `CrewWorkflow.run_final_analysis` devolve `extracao` vazio; se precisar do agregado, injete-o na resposta.
- Tratamento de deduplicação em `_aggregate_extractions` está como TODO.
- Falha total de chunks gera `ValueError` (retorna 500 via router) — avaliar mensagens ao cliente.

## Como estudar e navegar
- Comece pelo fluxo: `settings`/`utils` → modelos → serviços → CrewAI → LangGraph → router → `main.py`.
- Rode chamadas de teste: upload de PDF e análise; observe logs (configurados em `logger.py`).
- Ajuste env vars (`LAWERAI_*`) para trocar provider/modelo.


def get_logger(name: Optional[str] = None) -> Logger:
   """Retrieve a configured logger, defaulting to the root application logger."""
   return configure_logger(name or "lawerai")
```
- Configuração simples de logger com formatação padronizada.

### Sobre `business_router.py`
- Existe router para `/business`, mas o arquivo `domain/models/business_models.py` referenciado não está no projeto; rotas usarão um repositório inexistente e falharão se incluídas. Atualmente `main.py` não inclui esse router, então permanece inativo.

## Possíveis pontos de atenção
- `DocumentRepository` é in-memory: reiniciar a aplicação perde uploads; considere persistência real.
- `CrewWorkflow.run_final_analysis` devolve `extracao` vazio; se precisar do agregado, injete-o na resposta.
- Tratamento de deduplicação em `_aggregate_extractions` está como TODO.
- Falha total de chunks gera `ValueError` (retorna 500 via router) — avaliar mensagens ao cliente.

## Como estudar e navegar
- Comece pelo fluxo: `main.py` → `document_router.py` → `graph_builder.py` → serviços de domínio → fluxo CrewAI.
- Rode chamadas de teste: upload de PDF e análise; observe logs (configurados em `logger.py`).
- Ajuste env vars (`LAWERAI_*`) para trocar provider/modelo.

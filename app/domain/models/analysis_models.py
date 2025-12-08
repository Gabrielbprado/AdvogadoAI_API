"""Structured models for agent-driven analysis outputs."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ClausulaRelevante(BaseModel):
    """Cláusulas destacadas pelo agente leitor."""

    model_config = ConfigDict(extra="ignore")

    numero: Optional[str] = None
    descricao: str = ""
    detalhes: Optional[str] = None


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
    clausulas_relevantes: List[ClausulaRelevante] = Field(default_factory=list)
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

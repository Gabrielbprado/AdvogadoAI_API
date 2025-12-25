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
    "avisos": [
        {"aviso": "", "detalhe": "", "trecho": ""}
    ],
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

    def _build_task(self, agent: Agent, prompt: str, expected: dict, user_context: str | None = None) -> Task:
        contextual = f"\n\nDiretrizes do usuário:\n{user_context}" if user_context else ""
        full_description = f"{prompt}{contextual}\n\n{_PT_JSON_DIRECTIVE}"
        return Task(
            description=full_description,
            expected_output=json.dumps(expected, ensure_ascii=False),
            agent=agent,
        )

    def create_reader_task(self, agent: Agent, user_context: str | None = None) -> Task:
        prompt = (
            "Analise o trecho do contrato e extraia TODAS as cláusulas presentes nele. "
            "Se houver cláusulas numeradas (1, 2, 3...), capture o número, o título e o texto completo. "
            "Não resuma o texto da cláusula. "
            "Também extraia tópicos principais, partes, valores e datas."
        )
        return self._build_task(agent, prompt, READER_EXPECTED_JSON, user_context)

    def create_analyst_task(self, agent: Agent, user_context: str | None = None) -> Task:
        prompt = (
            "A partir da extracao do leitor, detalhe riscos juridicos, inconsistencias, clausulas abusivas "
            "e melhorias recomendadas. "
            "Responda explicitamente ao(s) aviso(s) prioritario(s) do usuario em um campo 'avisos': "
            "para cada aviso, devolva {aviso, detalhe, trecho}. "
            "Se houver ocorrencias, explique o porquê e cite o trecho/referencia. Se nao houver, use detalhe='sem ocorrencias' e deixe trecho vazio."
        )
        return self._build_task(agent, prompt, ANALYST_EXPECTED_JSON, user_context)

    def create_writer_task(self, agent: Agent, user_context: str | None = None) -> Task:
        prompt = (
            "Consolide todo o estudo em parecer resumido, parecer detalhado e contra-proposta juridica."
        )
        return self._build_task(agent, prompt, LAWYER_EXPECTED_JSON, user_context)


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
    data["avisos"] = _coerce_alerts(data.get("avisos"))
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


def _coerce_alerts(value: Any) -> List[dict]:
    """Normalize avisos into list of {aviso, detalhe, trecho}."""
    if not value:
        return []
    items = value if isinstance(value, list) else [value]
    alerts: List[dict] = []
    for item in items:
        if isinstance(item, dict):
            alerts.append(
                {
                    "aviso": _coerce_string(item.get("aviso") or item.get("alerta") or item.get("titulo")),
                    "detalhe": _coerce_string(item.get("detalhe") or item.get("descricao") or item.get("motivo")),
                    "trecho": _coerce_string(item.get("trecho") or item.get("referencia") or item.get("onde")),
                }
            )
        else:
            text = _coerce_string(item)
            if text:
                alerts.append({"aviso": text, "detalhe": text, "trecho": ""})
    return alerts


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

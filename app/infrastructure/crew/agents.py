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

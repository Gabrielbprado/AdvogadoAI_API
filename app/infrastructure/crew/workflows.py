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

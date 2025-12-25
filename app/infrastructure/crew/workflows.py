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

    def run(self, document_text: str, user_context: str | None = None) -> FinalAnalysisResponse:
        """Execute the CrewAI crew sequentially and parse the outputs."""
        # Legacy method, kept for compatibility or full-text runs
        reader_agent = self._agent_factory.create_reader()
        analyst_agent = self._agent_factory.create_analyst()
        writer_agent = self._agent_factory.create_writer()

        reader_task = self._task_factory.create_reader_task(reader_agent, user_context)
        analyst_task = self._task_factory.create_analyst_task(analyst_agent, user_context)
        writer_task = self._task_factory.create_writer_task(writer_agent, user_context)

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

    def run_reader_chunk(self, chunk_text: str, user_context: str | None = None) -> ReaderExtraction:
        """Run only the Reader agent on a specific text chunk."""
        reader_agent = self._agent_factory.create_reader()
        reader_task = self._task_factory.create_reader_task(reader_agent, user_context)
        
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

    def run_final_analysis(self, aggregated_context: str, user_context: str | None = None) -> FinalAnalysisResponse:
        """Run Analyst and Writer on the aggregated context from all chunks."""
        analyst_agent = self._agent_factory.create_analyst()
        writer_agent = self._agent_factory.create_writer()

        analyst_task = self._task_factory.create_analyst_task(analyst_agent, user_context)
        writer_task = self._task_factory.create_writer_task(writer_agent, user_context)

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

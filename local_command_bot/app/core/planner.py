"""Planner Engine: Breaks natural language requirements into structured JobPlans and Tasks."""

import logging
from pathlib import Path
from typing import Optional

from app.core.models import (
    Job, Task, JobPlan, TaskPlanItem, TaskStatus, TaskRole, TokenUsage
)
from app.providers import get_adapter
from app.config.settings import PROMPTS_DIR

logger = logging.getLogger(__name__)


class PlannerError(Exception):
    """Raised when plan generation or validation fails."""
    pass


class PlannerEngine:
    """Orchestrates plan generation from user prompt using AI."""

    def __init__(self, system_prompt_path: Optional[Path] = None):
        self.prompt_file = system_prompt_path or (PROMPTS_DIR / "planner.md")
        self._system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        if self.prompt_file.exists():
            return self.prompt_file.read_text(encoding="utf-8")
        return "You are an expert Document Architecture Planner. Produce a structured JobPlan JSON."

    async def create_plan(
        self,
        user_prompt: str,
        provider_name: str = "openai",
        model: Optional[str] = None,
        budget_limit: float = 5.0,
        time_limit: float = 600.0,
        dry_run: bool = False,
    ) -> tuple[JobPlan, TokenUsage]:
        """Generate and validate a structured JobPlan from user input."""
        if not user_prompt or len(user_prompt.strip()) < 5:
            raise PlannerError("User prompt is too short to generate a meaningful plan.")

        # In dry run mode, force mock adapter
        actual_provider = "mock" if dry_run else provider_name
        adapter = get_adapter(actual_provider, model=model)

        formatted_input = (
            f"YÊU CẦU NGƯỜI DÙNG:\n{user_prompt}\n\n"
            f"THIẾT LẬP:\n"
            f"- Ngân sách tối đa: ${budget_limit:.2f} USD\n"
            f"- Thời gian tối đa: {time_limit:.0f} giây\n"
            f"Hãy phân tích và lập kế hoạch chi tiết thành JobPlan."
        )

        try:
            plan, usage = await adapter.generate_structured(
                prompt=formatted_input,
                schema_cls=JobPlan,
                system_prompt=self._system_prompt,
                model=model,
                temperature=0.2
            )
            # Override budget/time with user limits
            plan.budget_limit_usd = budget_limit
            plan.time_limit_seconds = time_limit

            self.validate_plan(plan)
            return plan, usage
        except Exception as e:
            logger.error(f"Failed to generate structured plan: {e}")
            raise PlannerError(f"Plan generation failed: {str(e)}")

    def validate_plan(self, plan: JobPlan) -> None:
        """Perform semantic validation on the generated JobPlan."""
        if not plan.objective or len(plan.objective.strip()) < 5:
            raise PlannerError("Invalid JobPlan: Objective is missing or empty.")

        if not plan.tasks or len(plan.tasks) == 0:
            raise PlannerError("Invalid JobPlan: Tasks list is empty.")

        task_ids = set()
        for idx, task_item in enumerate(plan.tasks):
            if not task_item.task_id:
                task_item.task_id = f"task_{idx + 1}"
            if task_item.task_id in task_ids:
                raise PlannerError(f"Invalid JobPlan: Duplicate task_id '{task_item.task_id}'.")
            task_ids.add(task_item.task_id)

            if not task_item.title:
                raise PlannerError(f"Invalid JobPlan: Task '{task_item.task_id}' has no title.")

            # Validate dependencies exist
            for dep in task_item.dependencies:
                if dep == task_item.task_id:
                    raise PlannerError(f"Invalid JobPlan: Task '{task_item.task_id}' cannot depend on itself.")

    def plan_to_tasks(self, job_id: str, plan: JobPlan, default_provider: str = "openai", default_model: str = "gpt-4o-mini") -> list[Task]:
        """Convert a validated JobPlan into concrete executable Task instances."""
        executable_tasks: list[Task] = []

        for idx, item in enumerate(plan.tasks):
            # If item has no dependencies, it's READY immediately; otherwise PENDING
            initial_status = TaskStatus.READY if not item.dependencies else TaskStatus.PENDING

            # Smart Routing: If user set default_provider to 'auto', preserve the Commander's chosen Cloud AI per task
            if default_provider in ("auto", "smart", "multi_cloud") and item.provider and item.provider != "mock":
                assigned_provider = item.provider
                assigned_model = item.model
            else:
                assigned_provider = default_provider or item.provider
                assigned_model = default_model or item.model

            task = Task(
                task_id=item.task_id,
                job_id=job_id,
                role=item.role,
                provider=assigned_provider,
                model=assigned_model,
                input={
                    "title": item.title,
                    "instructions": item.instructions,
                    "result_format": item.result_format,
                    "acceptance_criteria": item.acceptance_criteria,
                    "section_id": item.section_id or f"sec_{idx + 1}",
                    "section_order": item.section_order or (idx + 1),
                    "document_objective": plan.objective,
                    "references": plan.references_to_consult,
                },
                dependencies=item.dependencies,
                status=initial_status,
                attempt_count=0,
                max_attempts=3
            )
            executable_tasks.append(task)

        return executable_tasks

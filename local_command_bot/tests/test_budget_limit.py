"""Test 6: Clean stop when job spending exceeds budget limit."""

import pytest
from app.core.models import Job, JobStatus, Task, TaskRole, OutputFormat, JobPlan, TaskPlanItem
from app.core.orchestrator import Orchestrator, BudgetExceededError


@pytest.mark.asyncio
async def test_budget_exceeded_stops_job(temp_db, temp_output_dir):
    orch = Orchestrator(state_store=temp_db)

    # Job with a very low budget limit ($0.01)
    job = Job(
        job_id="job_budget_test",
        prompt="Test budget limit",
        status=JobStatus.RUNNING,
        budget_limit_usd=0.01,
        total_cost_usd=0.02,  # Already exceeded
        output_dir=str(temp_output_dir),
        output_formats=[OutputFormat.MD]
    )
    temp_db.save_job(job)

    # Add a mock plan and task
    job.plan = JobPlan(
        objective="Budget test",
        tasks=[TaskPlanItem(task_id="bt1", title="Task 1", role=TaskRole.WRITER, instructions="X")]
    )
    temp_db.save_task(Task(task_id="bt1", job_id=job.job_id, role=TaskRole.WRITER, provider="mock", model="m"))

    finished_job = await orch.run_job(job, default_provider="mock", default_model="mock-model")

    assert finished_job.status == JobStatus.FAILED
    assert "vượt trần ngân sách" in finished_job.error_message

"""Test Multi-Agent role separation: Commander, Worker, and Synthesizer tasks."""

import pytest
from app.core.models import Job, OutputFormat, JobStatus, TaskRole
from app.core.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_multi_agent_role_execution(temp_db, temp_output_dir):
    orch = Orchestrator(state_store=temp_db)

    job = Job(
        job_id="multi_agent_job_test",
        prompt="Soạn thảo SOP Thao tác đóng nắp chai tự động theo chuẩn GMP.",
        output_dir=str(temp_output_dir),
        output_formats=[OutputFormat.MD],
        dry_run=True
    )
    temp_db.save_job(job)

    finished_job = await orch.run_job(
        job=job,
        default_provider="mock",
        default_model="mock-model",
        planner_provider="mock",
        planner_model="mock-commander-model",
        writer_provider="mock",
        writer_model="mock-worker-model",
        reviewer_provider="mock",
        reviewer_model="mock-reviewer-model"
    )

    assert finished_job.status == JobStatus.SUCCEEDED

    # Verify tasks saved in SQLite
    tasks = temp_db.get_tasks_for_job(job.job_id)
    task_map = {t.task_id: t for t in tasks}

    # Verify T-PLANNER (Commander) exists and succeeded
    assert "T-PLANNER" in task_map
    assert task_map["T-PLANNER"].role == TaskRole.PLANNER
    assert task_map["T-PLANNER"].status == JobStatus.SUCCEEDED
    assert task_map["T-PLANNER"].model == "mock-commander-model"

    # Verify T-FINAL (Synthesizer / Auditor) exists and succeeded
    assert "T-FINAL" in task_map
    assert task_map["T-FINAL"].role == TaskRole.AUDITOR
    assert task_map["T-FINAL"].status == JobStatus.SUCCEEDED

    # Verify worker tasks have assigned worker model
    worker_tasks = [t for t in tasks if t.task_id not in ("T-PLANNER", "T-FINAL")]
    assert len(worker_tasks) > 0
    for wt in worker_tasks:
        assert wt.model == "mock-worker-model"

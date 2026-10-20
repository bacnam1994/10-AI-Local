"""Test 19: Ensures critical errors are captured and propagated to callbacks / UI."""

import pytest
from app.core.models import Job, JobStatus, OutputFormat
from app.core.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_critical_error_captured_in_job(temp_db, temp_output_dir):
    captured_logs = []
    captured_job_statuses = []

    def on_log(level, msg, tid):
        captured_logs.append((level, msg))

    def on_job_updated(job):
        captured_job_statuses.append(job.status)

    orch = Orchestrator(
        state_store=temp_db,
        on_job_updated=on_job_updated,
        on_log=on_log
    )

    # Short invalid prompt triggering PlannerError
    job = Job(
        job_id="err_prop_job",
        prompt="Hi",  # Too short
        output_dir=str(temp_output_dir),
        output_formats=[OutputFormat.MD]
    )
    temp_db.save_job(job)

    finished_job = await orch.run_job(job, default_provider="mock", default_model="mock-model")

    assert finished_job.status == JobStatus.FAILED
    assert finished_job.error_message is not None
    assert "too short" in finished_job.error_message.lower()

    # Check that ERROR log was emitted
    assert any(lvl == "ERROR" for lvl, _ in captured_logs)

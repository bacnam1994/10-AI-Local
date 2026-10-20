"""Test 7: Job cancellation terminates cleanly without hanging."""

import pytest
import asyncio
from app.core.models import Job, JobStatus, OutputFormat
from app.core.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_job_cancellation(temp_db, temp_output_dir):
    orch = Orchestrator(state_store=temp_db)

    job = Job(
        job_id="job_cancel_test",
        prompt="SOP test cancellation",
        status=JobStatus.PENDING,
        output_dir=str(temp_output_dir),
        output_formats=[OutputFormat.MD]
    )
    temp_db.save_job(job)

    # Cancel orchestrator after a brief delay
    async def cancel_later():
        await asyncio.sleep(0.05)
        orch.cancel()

    asyncio.create_task(cancel_later())

    res = await orch.run_job(job, default_provider="mock", default_model="mock-model")

    assert res.status == JobStatus.CANCELLED
    # Verify in SQLite database as well
    saved_job = temp_db.get_job(job.job_id)
    assert saved_job.status == JobStatus.CANCELLED

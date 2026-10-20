"""Test 8: SQLite persistence and crash recovery of interrupted jobs."""

import pytest
from app.core.models import Job, Task, JobStatus, TaskStatus, TaskRole, OutputFormat
from app.core.state_store import StateStore


def test_sqlite_persistence_and_recovery(temp_db):
    # Simulate a job left in RUNNING status due to abrupt crash
    job = Job(
        job_id="crash_job_1",
        prompt="SOP crashing simulation",
        status=JobStatus.RUNNING,
        output_dir="C:/fake_dir",
        output_formats=[OutputFormat.DOCX]
    )
    temp_db.save_job(job)

    task = Task(
        task_id="t_c1",
        job_id="crash_job_1",
        role=TaskRole.WRITER,
        provider="mock",
        model="m",
        status=TaskStatus.RUNNING
    )
    temp_db.save_task(task)

    # Trigger crash recovery
    recovered_jobs = temp_db.recover_interrupted_jobs()

    assert len(recovered_jobs) == 1
    assert recovered_jobs[0].job_id == "crash_job_1"
    assert recovered_jobs[0].status == JobStatus.PAUSED

    # Verify audit log was recorded
    logs = temp_db.get_logs("crash_job_1")
    assert any("Khôi phục phiên làm việc" in l["message"] for l in logs)

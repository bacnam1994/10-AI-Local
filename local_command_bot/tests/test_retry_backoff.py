"""Test 5: Retry with exponential backoff and jitter upon simulated errors."""

import pytest
from app.core.models import Task, TaskStatus, TaskRole, Job, OutputFormat
from app.core.scheduler import DAGScheduler
from app.providers.base import ProviderError


@pytest.mark.asyncio
async def test_retry_eventual_success(temp_db):
    scheduler = DAGScheduler(temp_db, max_concurrency=2)
    job_id = "j_retry"
    temp_db.save_job(Job(
        job_id=job_id,
        prompt="Test retry",
        output_dir="C:/tmp",
        output_formats=[OutputFormat.MD]
    ))
    task = Task(task_id="retry_t1", job_id=job_id, role=TaskRole.WRITER, provider="mock", model="m")
    temp_db.save_task(task)

    call_count = 0

    async def flaky_fn(t: Task) -> Task:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ProviderError("Simulated network blip (ECONNRESET)", is_transient=True)
        t.output_content = "Success on attempt 3"
        return t

    res = await scheduler.execute_task_with_retry(
        task,
        flaky_fn,
        max_retries=3,
        base_delay_seconds=0.01,
        max_delay_seconds=0.05
    )

    assert res.status == TaskStatus.SUCCEEDED
    assert res.attempt_count == 3
    assert "Success on attempt 3" in res.output_content


@pytest.mark.asyncio
async def test_retry_exhaustion_fails(temp_db):
    scheduler = DAGScheduler(temp_db, max_concurrency=2)
    job_id = "j_retry_fail"
    temp_db.save_job(Job(
        job_id=job_id,
        prompt="Test retry fail",
        output_dir="C:/tmp",
        output_formats=[OutputFormat.MD]
    ))
    task = Task(task_id="fail_t1", job_id=job_id, role=TaskRole.WRITER, provider="mock", model="m")
    temp_db.save_task(task)

    async def always_fails(t: Task) -> Task:
        raise ProviderError("Persistent network outage", is_transient=True)

    res = await scheduler.execute_task_with_retry(
        task,
        always_fails,
        max_retries=2,
        base_delay_seconds=0.01,
        max_delay_seconds=0.05
    )

    assert res.status == TaskStatus.FAILED
    assert res.attempt_count > 2
    assert "Persistent network outage" in res.error_message

"""Test 4: Parallel execution of independent tasks."""

import pytest
import asyncio
from app.core.models import Task, TaskStatus, TaskRole, Job, OutputFormat
from app.core.scheduler import DAGScheduler


@pytest.mark.asyncio
async def test_independent_tasks_run_in_parallel(temp_db):
    scheduler = DAGScheduler(temp_db, max_concurrency=3)
    job_id = "job_parallel_1"
    temp_db.save_job(Job(
        job_id=job_id,
        prompt="Test parallel",
        output_dir="C:/tmp",
        output_formats=[OutputFormat.MD]
    ))
    tasks = [
        Task(task_id="t1", job_id=job_id, role=TaskRole.RESEARCHER, provider="mock", model="m", dependencies=[]),
        Task(task_id="t2", job_id=job_id, role=TaskRole.RESEARCHER, provider="mock", model="m", dependencies=[]),
        Task(task_id="t3", job_id=job_id, role=TaskRole.RESEARCHER, provider="mock", model="m", dependencies=[]),
    ]
    for t in tasks:
        temp_db.save_task(t)

    runnable = scheduler.get_runnable_tasks(job_id)
    assert len(runnable) == 3

    execution_order = []

    async def mock_exec(t: Task) -> Task:
        execution_order.append(f"start_{t.task_id}")
        await asyncio.sleep(0.05)
        execution_order.append(f"end_{t.task_id}")
        t.output_content = "done"
        return t

    results = await asyncio.gather(*[
        scheduler.execute_task_with_retry(t, mock_exec) for t in runnable
    ])

    assert len(results) == 3
    assert all(r.status == TaskStatus.SUCCEEDED for r in results)
    # Starts happened before all ends
    assert execution_order[0].startswith("start_")
    assert execution_order[1].startswith("start_")

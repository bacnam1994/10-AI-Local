"""DAG Task Scheduler and Concurrency Controller."""

import asyncio
import random
import logging
from typing import Callable, Coroutine, Any, Optional

from app.core.models import Task, TaskStatus, Job
from app.core.state_store import StateStore

logger = logging.getLogger(__name__)


class DependencyCycleError(ValueError):
    """Raised when task dependencies contain a cycle."""
    pass


class MissingDependencyError(ValueError):
    """Raised when a task depends on a non-existent task."""
    pass


class DAGScheduler:
    """Manages DAG dependency resolution, topological ordering, and concurrency pool."""

    def __init__(self, state_store: StateStore, max_concurrency: int = 3):
        self.state_store = state_store
        self.max_concurrency = max(1, max_concurrency)
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

    def validate_dag(self, tasks: list[Task]) -> list[str]:
        """Validate that tasks form a valid Directed Acyclic Graph (DAG).
        Returns topographically sorted task IDs.
        Raises DependencyCycleError or MissingDependencyError if invalid.
        """
        task_map = {t.task_id: t for t in tasks}
        in_degree = {t.task_id: 0 for t in tasks}
        graph: dict[str, list[str]] = {t.task_id: [] for t in tasks}

        for task in tasks:
            for dep in task.dependencies:
                if dep not in task_map:
                    raise MissingDependencyError(
                        f"Task '{task.task_id}' depends on undefined task '{dep}'"
                    )
                graph[dep].append(task.task_id)
                in_degree[task.task_id] += 1

        # Kahn's algorithm for topological sorting
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        sorted_ids: list[str] = []

        while queue:
            curr = queue.pop(0)
            sorted_ids.append(curr)

            for neighbor in graph[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_ids) != len(tasks):
            remaining = set(task_map.keys()) - set(sorted_ids)
            raise DependencyCycleError(
                f"Cyclic dependency detected among tasks: {list(remaining)}"
            )

        return sorted_ids

    def get_runnable_tasks(self, job_id: str) -> list[Task]:
        """Identify tasks that are READY or PENDING whose dependencies have all SUCCEEDED."""
        all_tasks = self.state_store.get_tasks_for_job(job_id)
        task_map = {t.task_id: t for t in all_tasks}
        runnable: list[Task] = []

        for t in all_tasks:
            if t.status in (TaskStatus.PENDING, TaskStatus.READY, TaskStatus.RETRYING):
                # Check all dependencies
                all_deps_succeeded = True
                for dep_id in t.dependencies:
                    dep_task = task_map.get(dep_id)
                    if not dep_task or dep_task.status != TaskStatus.SUCCEEDED:
                        all_deps_succeeded = False
                        break

                if all_deps_succeeded:
                    if t.status != TaskStatus.READY:
                        t.status = TaskStatus.READY
                        self.state_store.save_task(t)
                    runnable.append(t)

        return runnable

    async def execute_task_with_retry(
        self,
        task: Task,
        executor_fn: Callable[[Task], Coroutine[Any, Any, Task]],
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 10.0,
    ) -> Task:
        """Execute a task with concurrency limiting and exponential backoff + jitter."""
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            self.state_store.save_task(task)
            self.state_store.append_log(
                task.job_id, "INFO",
                f"Bắt đầu thực thi nhiệm vụ: [{task.task_id}] (Vai trò: {task.role.value})",
                task_id=task.task_id
            )

            attempt = 0
            while attempt <= max_retries:
                attempt += 1
                task.attempt_count = attempt
                try:
                    # Run the executor coroutine
                    task = await executor_fn(task)
                    task.status = TaskStatus.SUCCEEDED
                    task.error_message = None
                    self.state_store.save_task(task)
                    self.state_store.append_log(
                        task.job_id, "INFO",
                        f"Nhiệm vụ [{task.task_id}] thành công (Lần thử {attempt}).",
                        task_id=task.task_id
                    )
                    return task

                except Exception as ex:
                    error_msg = str(ex)
                    task.error_message = error_msg
                    logger.warning(f"Task {task.task_id} failed on attempt {attempt}: {error_msg}")

                    if attempt > max_retries:
                        task.status = TaskStatus.FAILED
                        self.state_store.save_task(task)
                        self.state_store.append_log(
                            task.job_id, "ERROR",
                            f"Nhiệm vụ [{task.task_id}] thất bại sau {attempt} lần thử. Lỗi: {error_msg}",
                            task_id=task.task_id
                        )
                        return task

                    # Retry with exponential backoff + jitter
                    task.status = TaskStatus.RETRYING
                    self.state_store.save_task(task)
                    
                    delay = min(max_delay_seconds, base_delay_seconds * (2 ** (attempt - 1)))
                    jitter = random.uniform(0.1, 0.5)
                    total_delay = delay + jitter

                    self.state_store.append_log(
                        task.job_id, "WARN",
                        f"Nhiệm vụ [{task.task_id}] lỗi: {error_msg}. Thử lại sau {total_delay:.1f}s (Lần thử {attempt}/{max_retries}).",
                        task_id=task.task_id
                    )
                    await asyncio.sleep(total_delay)

            return task

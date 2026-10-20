"""Job Manager: High-level lifecycle coordinator, thread executor, and crash recovery."""

import uuid
import asyncio
import logging
from typing import Optional, Callable
from pathlib import Path

from app.core.models import Job, Task, JobStatus, OutputFormat, utc_now
from app.core.state_store import StateStore
from app.core.orchestrator import Orchestrator
from app.config.settings import settings

logger = logging.getLogger(__name__)


class JobManager:
    """Manages active and historical Jobs, event callbacks, and orchestrator lifecycle."""

    def __init__(
        self,
        state_store: Optional[StateStore] = None,
        on_job_updated: Optional[Callable[[Job], None]] = None,
        on_task_updated: Optional[Callable[[Task], None]] = None,
        on_log: Optional[Callable[[str, str, Optional[str]], None]] = None,
    ):
        self.state_store = state_store or StateStore(settings.db_path)
        self.on_job_updated = on_job_updated
        self.on_task_updated = on_task_updated
        self.on_log = on_log

        self._active_orchestrators: dict[str, Orchestrator] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}

    def create_job(
        self,
        prompt: str,
        output_formats: Optional[list[OutputFormat]] = None,
        output_dir: Optional[str] = None,
        budget_limit_usd: float = 5.0,
        max_concurrency: int = 3,
        max_retries: int = 3,
        timeout_seconds: float = 90.0,
        dry_run: bool = False,
    ) -> Job:
        """Create and persist a new Job in SQLite."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        formats = output_formats or [OutputFormat.DOCX, OutputFormat.MD]
        out_dir = output_dir or str(settings.outputs_dir / job_id)

        job = Job(
            job_id=job_id,
            prompt=prompt,
            status=JobStatus.PENDING,
            output_formats=formats,
            output_dir=out_dir,
            budget_limit_usd=budget_limit_usd,
            max_concurrency=max_concurrency,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            dry_run=dry_run,
            created_at=utc_now(),
            updated_at=utc_now()
        )

        self.state_store.save_job(job)
        self.state_store.append_log(job_id, "INFO", f"Khởi tạo phiên làm việc mới: [{job_id}]")
        if self.on_job_updated:
            self.on_job_updated(job)

        return job

    async def start_job(
        self,
        job_id: str,
        default_provider: str = "openai",
        default_model: str = "gpt-4o-mini",
        planner_provider: Optional[str] = None,
        planner_model: Optional[str] = None,
        writer_provider: Optional[str] = None,
        writer_model: Optional[str] = None,
        reviewer_provider: Optional[str] = None,
        reviewer_model: Optional[str] = None,
    ) -> Job:
        """Start or execute a job using an Orchestrator."""
        job = self.state_store.get_job(job_id)
        if not job:
            raise ValueError(f"Job '{job_id}' not found.")

        orchestrator = Orchestrator(
            state_store=self.state_store,
            on_job_updated=self.on_job_updated,
            on_task_updated=self.on_task_updated,
            on_log=self.on_log
        )
        self._active_orchestrators[job_id] = orchestrator

        try:
            finished_job = await orchestrator.run_job(
                job=job,
                default_provider=default_provider,
                default_model=default_model,
                planner_provider=planner_provider,
                planner_model=planner_model,
                writer_provider=writer_provider,
                writer_model=writer_model,
                reviewer_provider=reviewer_provider,
                reviewer_model=reviewer_model,
            )
            return finished_job
        finally:
            self._active_orchestrators.pop(job_id, None)

    def pause_job(self, job_id: str) -> bool:
        """Pause currently running orchestrator."""
        orch = self._active_orchestrators.get(job_id)
        if orch:
            orch.pause()
            return True
        return False

    def resume_job(self, job_id: str) -> bool:
        """Resume paused orchestrator."""
        orch = self._active_orchestrators.get(job_id)
        if orch:
            orch.resume()
            return True
        return False

    def cancel_job(self, job_id: str) -> bool:
        """Cancel running orchestrator."""
        orch = self._active_orchestrators.get(job_id)
        if orch:
            orch.cancel()
            return True
        return False

    def recover_crashed_jobs(self) -> list[Job]:
        """Detect and restore any unfinished jobs from database."""
        return self.state_store.recover_interrupted_jobs()

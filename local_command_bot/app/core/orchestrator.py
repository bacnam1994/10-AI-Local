"""Master Orchestrator: Coordinates DAG scheduling, AI workflows, and Document synthesis."""

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional, Any

from app.core.models import (
    Job, Task, JobStatus, TaskStatus, TaskRole, OutputFormat,
    JobPlan, ReviewResult, TokenUsage, SourceReference, utc_now
)
from app.core.state_store import StateStore
from app.core.scheduler import DAGScheduler
from app.core.planner import PlannerEngine
from app.core.writer import WriterEngine
from app.core.reviewer import ReviewerEngine
from app.research.researcher import ResearchEngine
from app.document.docx_builder import DocxBuilder
from app.document.pdf_builder import PdfBuilder
from app.document.md_builder import MarkdownBuilder
from app.document.validators import DocumentValidator
from app.security.sanitizer import resolve_safe_output_path
from app.config.settings import settings

logger = logging.getLogger(__name__)


class BudgetExceededError(Exception):
    """Raised when estimated job cost exceeds the defined budget limit."""
    pass


class Orchestrator:
    """Coordinates End-to-End Execution of a Job."""

    def __init__(
        self,
        state_store: StateStore,
        on_job_updated: Optional[Callable[[Job], None]] = None,
        on_task_updated: Optional[Callable[[Task], None]] = None,
        on_log: Optional[Callable[[str, str, Optional[str]], None]] = None,
    ):
        self.state_store = state_store
        self.on_job_updated = on_job_updated
        self.on_task_updated = on_task_updated
        self.on_log = on_log

        # Sub-engines
        self.planner = PlannerEngine()
        self.writer = WriterEngine()
        self.reviewer = ReviewerEngine()
        self.researcher = ResearchEngine(state_store)
        self.docx_builder = DocxBuilder()
        self.pdf_builder = PdfBuilder()
        self.md_builder = MarkdownBuilder()
        self.validator = DocumentValidator()

        # Control flags
        self._is_paused = False
        self._is_cancelled = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially

    def pause(self) -> None:
        """Pause job execution safely."""
        self._is_paused = True
        self._pause_event.clear()

    def resume(self) -> None:
        """Resume paused job execution."""
        self._is_paused = False
        self._pause_event.set()

    def cancel(self) -> None:
        """Cancel job execution."""
        self._is_cancelled = True
        self._pause_event.set()  # Unblock if currently paused

    def _log(self, job_id: str, level: str, message: str, task_id: Optional[str] = None) -> None:
        self.state_store.append_log(job_id, level, message, task_id=task_id)
        if self.on_log:
            self.on_log(level, message, task_id)

    def _notify_job(self, job: Job) -> None:
        self.state_store.save_job(job)
        if self.on_job_updated:
            self.on_job_updated(job)

    def _notify_task(self, task: Task) -> None:
        self.state_store.save_task(task)
        if self.on_task_updated:
            self.on_task_updated(task)

    async def run_job(
        self,
        job: Job,
        default_provider: str = "openai",
        default_model: str = "gpt-4o-mini",
        planner_provider: Optional[str] = None,
        planner_model: Optional[str] = None,
        writer_provider: Optional[str] = None,
        writer_model: Optional[str] = None,
        reviewer_provider: Optional[str] = None,
        reviewer_model: Optional[str] = None,
    ) -> Job:
        """Execute complete lifecycle of a Job."""
        self._is_paused = False
        self._is_cancelled = False
        self._pause_event.set()

        planner_prov = planner_provider or default_provider
        planner_mod = planner_model or default_model
        writer_prov = writer_provider or default_provider
        writer_mod = writer_model or default_model
        reviewer_prov = reviewer_provider or default_provider
        reviewer_mod = reviewer_model or default_model

        self._reviewer_prov = reviewer_prov
        self._reviewer_mod = reviewer_mod

        try:
            # 1. Planning Phase (if not already planned)
            if not job.plan:
                job.status = JobStatus.PLANNING
                self._notify_job(job)
                self._log(
                    job.job_id, "INFO",
                    f"AI Tổng Chỉ Huy ({planner_prov} / {planner_mod}): Bắt đầu phân tích yêu cầu và lập kế hoạch công việc (JobPlan)..."
                )

                plan_task = Task(
                    task_id="T-PLANNER",
                    job_id=job.job_id,
                    role=TaskRole.PLANNER,
                    provider=planner_prov,
                    model=planner_mod,
                    input={
                        "title": "AI Tổng Chỉ Huy: Phân tích Yêu cầu & Thiết kế Đồ thị DAG",
                        "instructions": job.prompt
                    },
                    status=TaskStatus.RUNNING,
                    dependencies=[]
                )
                self._notify_task(plan_task)

                plan, plan_usage = await self.planner.create_plan(
                    user_prompt=job.prompt,
                    provider_name=planner_prov,
                    model=planner_mod,
                    budget_limit=job.budget_limit_usd,
                    time_limit=job.timeout_seconds,
                    dry_run=job.dry_run
                )
                job.plan = plan
                job.total_tokens += plan_usage.total_tokens
                job.total_cost_usd += plan_usage.estimated_cost_usd
                self._notify_job(job)

                plan_task.status = TaskStatus.SUCCEEDED
                plan_task.output_content = (
                    f"Đã lập kế hoạch DAG thành công. Mục tiêu: '{plan.objective}' ({len(plan.tasks)} nhiệm vụ)."
                )
                plan_task.usage = plan_usage
                self._notify_task(plan_task)

                # Convert plan into tasks in state store using writer_prov, writer_mod
                tasks = self.planner.plan_to_tasks(job.job_id, plan, writer_prov, writer_mod)
                for t in tasks:
                    self._notify_task(t)

                self._log(
                    job.job_id, "INFO",
                    f"AI Tổng Chỉ Huy đã phê duyệt kế hoạch. Đã phân công {len(tasks)} nhiệm vụ cho Cloud Worker ({writer_prov}). Mục tiêu: '{plan.objective}'."
                )

            # 2. Research Phase
            if job.plan and job.plan.references_to_consult:
                self._log(job.job_id, "INFO", "Tiến hành tra cứu và xác minh các quy chuẩn quy định...")
                await self.researcher.research_for_job(job.job_id, job.plan.references_to_consult)

            # 3. Task Execution Loop via DAG Scheduler
            job.status = JobStatus.RUNNING
            self._notify_job(job)

            scheduler = DAGScheduler(self.state_store, max_concurrency=job.max_concurrency)
            all_tasks = self.state_store.get_tasks_for_job(job.job_id)

            # Validate DAG structure
            scheduler.validate_dag(all_tasks)

            # Loop until all tasks finish, fail, or cancel
            while True:
                # Check for cancellation
                if self._is_cancelled:
                    job.status = JobStatus.CANCELLED
                    self._notify_job(job)
                    self._log(job.job_id, "WARN", "Tiến trình công việc đã bị người dùng hủy bỏ.")
                    return job

                # Check for pause
                if self._is_paused:
                    job.status = JobStatus.PAUSED
                    self._notify_job(job)
                    self._log(job.job_id, "WARN", "Tiến trình công việc tạm dừng. Đang chờ người dùng tiếp tục (Resume)...")
                    await self._pause_event.wait()
                    if self._is_cancelled:
                        job.status = JobStatus.CANCELLED
                        self._notify_job(job)
                        return job
                    job.status = JobStatus.RUNNING
                    self._notify_job(job)

                # Check budget limit
                if job.total_cost_usd >= job.budget_limit_usd:
                    job.status = JobStatus.FAILED
                    job.error_message = (
                        f"Dừng công việc: Chi phí ước tính (${job.total_cost_usd:.4f}) đã vượt trần ngân sách (${job.budget_limit_usd:.2f})"
                    )
                    self._notify_job(job)
                    self._log(job.job_id, "ERROR", job.error_message)
                    raise BudgetExceededError(job.error_message)

                # Check runnable tasks
                runnable_tasks = scheduler.get_runnable_tasks(job.job_id)
                current_all_tasks = self.state_store.get_tasks_for_job(job.job_id)

                # Check completion conditions
                incomplete_tasks = [
                    t for t in current_all_tasks
                    if t.status in (TaskStatus.PENDING, TaskStatus.READY, TaskStatus.RUNNING, TaskStatus.RETRYING)
                ]
                failed_tasks = [t for t in current_all_tasks if t.status == TaskStatus.FAILED]

                if failed_tasks:
                    job.status = JobStatus.FAILED
                    job.error_message = f"Một hoặc nhiều nhiệm vụ con thất bại: {[t.task_id for t in failed_tasks]}"
                    self._notify_job(job)
                    self._log(job.job_id, "ERROR", job.error_message)
                    return job

                if not incomplete_tasks:
                    # All tasks succeeded!
                    self._log(job.job_id, "INFO", "Toàn bộ nhiệm vụ trong đồ thị DAG đã hoàn thành thành công.")
                    break

                if not runnable_tasks:
                    # Waiting for running tasks or deadlock
                    running = [t for t in current_all_tasks if t.status == TaskStatus.RUNNING]
                    if not running:
                        # Deadlock or unmet dependencies
                        job.status = JobStatus.FAILED
                        job.error_message = "Không có nhiệm vụ nào sẵn sàng chạy mặc dù vẫn còn nhiệm vụ chưa hoàn tất (Bế tắc phụ thuộc)."
                        self._notify_job(job)
                        self._log(job.job_id, "ERROR", job.error_message)
                        return job
                    await asyncio.sleep(0.3)
                    continue

                # Launch runnable tasks up to max_concurrency
                async def _worker(task_item: Task) -> Task:
                    return await scheduler.execute_task_with_retry(
                        task=task_item,
                        executor_fn=lambda t: self._execute_task_logic(t, job),
                        max_retries=job.max_retries
                    )

                # Execute batch concurrently
                results = await asyncio.gather(*[_worker(t) for t in runnable_tasks], return_exceptions=True)

                for r in results:
                    if isinstance(r, Task):
                        job.total_tokens += r.usage.total_tokens
                        job.total_cost_usd += r.usage.estimated_cost_usd
                        self._notify_task(r)
                    elif isinstance(r, Exception):
                        logger.error(f"Task batch exception: {r}")

                self._notify_job(job)

            # 4. Synthesis & Document Building Phase
            self._log(
                job.job_id, "INFO",
                f"AI Tổng Chỉ Huy ({planner_prov} / {planner_mod}): Tiến hành kiểm định, tổng hợp tài liệu và xuất bản (DOCX, PDF, Markdown)..."
            )

            synth_task = Task(
                task_id="T-FINAL",
                job_id=job.job_id,
                role=TaskRole.AUDITOR,
                provider=planner_prov,
                model=planner_mod,
                input={
                    "title": "AI Tổng Chỉ Huy: Kiểm Định, Tổng Hợp & Xuất Bản Toàn Văn",
                    "instructions": "Tổng hợp các phân đoạn, kiểm định tính toàn vẹn và tạo tài liệu DOCX, PDF, MD",
                    "section_order": 9999
                },
                status=TaskStatus.RUNNING,
                dependencies=[t.task_id for t in self.state_store.get_tasks_for_job(job.job_id) if t.task_id != "T-PLANNER"]
            )
            self._notify_task(synth_task)

            generated_files = await self._synthesize_documents(job)
            job.generated_files = generated_files

            synth_task.status = TaskStatus.SUCCEEDED
            synth_task.output_content = f"Đã xuất bản thành công {len(generated_files)} tệp: {', '.join(Path(f).name for f in generated_files)}"
            self._notify_task(synth_task)

            job.status = JobStatus.SUCCEEDED
            job.completed_at = utc_now()
            self._notify_job(job)
            self._log(
                job.job_id, "INFO",
                f"AI Tổng Chỉ Huy hoàn tất toàn bộ quy trình xuất sắc! Đã tạo các tệp: {', '.join(Path(f).name for f in generated_files)}"
            )
            return job

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            self._notify_job(job)
            self._log(job.job_id, "ERROR", f"Công việc thất bại với lỗi: {str(e)}")
            return job

    async def _execute_task_logic(self, task: Task, job: Job) -> Task:
        """Internal business logic for executing a single task with Reviewer loop."""
        if task.role == TaskRole.RESEARCHER:
            refs = await self.researcher.research_for_job(job.job_id, [task.input.get("instructions", "")])
            task.output_content = f"Đã tra cứu {len(refs)} tài liệu tham chiếu."
            return task

        # WRITER / REVIEWER loop
        accumulated_context = ""
        # Get outputs of completed previous tasks for context continuity
        all_tasks = self.state_store.get_tasks_for_job(job.job_id)
        for prev in all_tasks:
            if prev.task_id != task.task_id and prev.status == TaskStatus.SUCCEEDED and prev.output_content and prev.task_id not in ("T-PLANNER", "T-FINAL"):
                accumulated_context += f"\n\n### {prev.input.get('title', '')}\n{prev.output_content}"

        round_num = 0
        max_rounds = settings.max_review_rounds
        critiques_to_fix: list[str] = []

        while round_num <= max_rounds:
            round_num += 1
            # Step 1: Draft section
            draft, usage = await self.writer.draft_section(
                task=task,
                previous_context=accumulated_context,
                critiques_to_fix=critiques_to_fix,
                dry_run=job.dry_run
            )
            task.output_content = draft
            task.usage.prompt_tokens += usage.prompt_tokens
            task.usage.completion_tokens += usage.completion_tokens
            task.usage.total_tokens += usage.total_tokens
            task.usage.estimated_cost_usd += usage.estimated_cost_usd

            # Step 2: Quality Review
            rev_prov = getattr(self, "_reviewer_prov", task.provider)
            rev_model = getattr(self, "_reviewer_mod", task.model)
            review_res, rev_usage = await self.reviewer.review_section(
                task=task,
                content=draft,
                provider=rev_prov,
                model=rev_model,
                dry_run=job.dry_run
            )
            task.review_result = review_res
            task.usage.prompt_tokens += rev_usage.prompt_tokens
            task.usage.completion_tokens += rev_usage.completion_tokens
            task.usage.total_tokens += rev_usage.total_tokens
            task.usage.estimated_cost_usd += rev_usage.estimated_cost_usd

            if review_res.is_approved or round_num > max_rounds:
                if not review_res.is_approved:
                    self._log(
                        job.job_id, "WARN",
                        f"Nhiệm vụ [{task.task_id}] đã đạt giới hạn {max_rounds} vòng sửa. Chấp thuận bản tốt nhất hiện có.",
                        task_id=task.task_id
                    )
                else:
                    self._log(
                        job.job_id, "INFO",
                        f"Nhiệm vụ [{task.task_id}] đạt chuẩn chất lượng (Điểm: {review_res.score:.1f}/10).",
                        task_id=task.task_id
                    )
                break

            # Collect critique fixes for next round
            critiques_to_fix = [f"[{c.severity}] {c.suggested_fix}" for c in review_res.critiques]
            self._log(
                job.job_id, "WARN",
                f"Nhiệm vụ [{task.task_id}] chưa đạt chuẩn (Vòng {round_num}). Yêu cầu sửa: {len(critiques_to_fix)} điểm tồn đọng.",
                task_id=task.task_id
            )

        return task

    async def _synthesize_documents(self, job: Job) -> list[str]:
        """Aggregate completed tasks, run validators, and output DOCX, PDF, and MD files."""
        tasks = self.state_store.get_tasks_for_job(job.job_id)
        references = self.state_store.get_source_references(job.job_id)

        # Collect ordered sections (filter out T-PLANNER and T-FINAL metadata tasks)
        writer_tasks = [
            t for t in tasks
            if t.output_content and t.role in (TaskRole.WRITER, TaskRole.AUDITOR) and t.task_id not in ("T-PLANNER", "T-FINAL")
        ]
        # Sort by section_order
        writer_tasks.sort(key=lambda t: t.input.get("section_order", 999))

        sections: list[tuple[str, str]] = []
        full_text_corpus = ""

        for t in writer_tasks:
            title = t.input.get("title", f"Mục {t.task_id}")
            content = t.output_content or ""
            sections.append((title, content))
            full_text_corpus += f"\n{title}\n{content}\n"

        # Validate document
        expected_sections = [t.input.get("title", "") for t in writer_tasks]
        mandatory_refs = [r.title for r in references if r.is_mandatory]
        report = self.validator.validate(
            full_text=full_text_corpus,
            expected_sections=expected_sections,
            mandatory_references=mandatory_refs
        )

        if report.placeholders_found:
            self._log(
                job.job_id, "WARN",
                f"Phát hiện placeholder còn sót: {report.placeholders_found[:5]}. Đã ghi chú tự động."
            )

        # Base output directory
        out_dir = Path(job.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        base_filename = f"SOP_{job.job_id[:8]}"
        created_paths: list[str] = []

        # 1. Output DOCX
        if OutputFormat.DOCX in job.output_formats or "DOCX" in job.output_formats:
            docx_target = resolve_safe_output_path(out_dir, f"{base_filename}.docx", allow_overwrite=False)
            self.docx_builder.build(
                job=job,
                sections=sections,
                references=references,
                output_file=docx_target,
                doc_code=f"SOP-{job.job_id[:6].upper()}",
                version="1.0"
            )
            created_paths.append(str(docx_target))

        # 2. Output PDF
        if OutputFormat.PDF in job.output_formats or "PDF" in job.output_formats:
            pdf_target = resolve_safe_output_path(out_dir, f"{base_filename}.pdf", allow_overwrite=False)
            try:
                self.pdf_builder.build(
                    job=job,
                    sections=sections,
                    references=references,
                    output_file=pdf_target,
                    doc_code=f"SOP-{job.job_id[:6].upper()}",
                    version="1.0"
                )
                created_paths.append(str(pdf_target))
            except Exception as e:
                self._log(job.job_id, "WARN", f"Không thể xuất PDF: {e}")

        # 3. Output Markdown
        if OutputFormat.MD in job.output_formats or "MD" in job.output_formats:
            md_target = resolve_safe_output_path(out_dir, f"{base_filename}.md", allow_overwrite=False)
            self.md_builder.build(
                job=job,
                sections=sections,
                references=references,
                output_file=md_target,
                doc_code=f"SOP-{job.job_id[:6].upper()}",
                version="1.0"
            )
            created_paths.append(str(md_target))

        return created_paths

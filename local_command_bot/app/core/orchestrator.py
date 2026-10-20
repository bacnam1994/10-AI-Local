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

    def _resolve_routing(
        self,
        job: Job,
        default_provider: str,
        default_model: str,
        planner_provider: Optional[str],
        planner_model: Optional[str],
        writer_provider: Optional[str],
        writer_model: Optional[str],
        reviewer_provider: Optional[str],
        reviewer_model: Optional[str],
    ) -> tuple[str, str, str, str, str, str]:
        """Resolve effective provider and model mappings for each stage."""
        if default_provider in ("mock", "test") or job.dry_run:
            planner_prov = planner_provider or "mock"
            planner_mod = planner_model or "mock-model"
            writer_prov = writer_provider or "mock"
            writer_mod = writer_model or "mock-model"
            reviewer_prov = reviewer_provider or "mock"
            reviewer_mod = reviewer_model or "mock-model"
        else:
            planner_prov = planner_provider or settings.default_planner_provider
            planner_mod = planner_model or settings.default_planner_model
            writer_prov = writer_provider or default_provider or settings.default_writer_provider
            writer_mod = writer_model or default_model or settings.default_writer_model
            reviewer_prov = reviewer_provider or writer_prov
            reviewer_mod = reviewer_model or writer_mod

        return planner_prov, planner_mod, writer_prov, writer_mod, reviewer_prov, reviewer_mod

    async def _run_planning_stage(
        self,
        job: Job,
        planner_prov: str,
        planner_mod: str,
        writer_prov: str,
        writer_mod: str
    ) -> None:
        """Stage 1: Analyze user request and generate structured task graph."""
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

        tasks = self.planner.plan_to_tasks(job.job_id, plan, writer_prov, writer_mod)
        for t in tasks:
            self._notify_task(t)

        self._log(
            job.job_id, "INFO",
            f"AI Tổng Chỉ Huy đã phê duyệt kế hoạch. Đã phân công {len(tasks)} nhiệm vụ cho Cloud Worker ({writer_prov}). Mục tiêu: '{plan.objective}'."
        )

    async def _run_research_stage(self, job: Job) -> None:
        """Stage 2: Lookup and track regulatory standards and references."""
        if job.plan and job.plan.references_to_consult:
            self._log(job.job_id, "INFO", "Tiến hành tra cứu danh mục quy chuẩn và tài liệu tham chiếu...")
            await self.researcher.research_for_job(job.job_id, job.plan.references_to_consult)

    async def _run_execution_stage(self, job: Job, scheduler: DAGScheduler) -> None:
        """Stage 3: Execute task graph via DAG scheduler with concurrency and retry control."""
        job.status = JobStatus.RUNNING
        self._notify_job(job)

        all_tasks = self.state_store.get_tasks_for_job(job.job_id)
        scheduler.validate_dag(all_tasks)

        while True:
            if self._is_cancelled:
                job.status = JobStatus.CANCELLED
                self._notify_job(job)
                self._log(job.job_id, "WARN", "Tiến trình công việc đã bị người dùng hủy bỏ.")
                return

            if self._is_paused:
                job.status = JobStatus.PAUSED
                self._notify_job(job)
                self._log(job.job_id, "WARN", "Tiến trình công việc tạm dừng. Đang chờ người dùng tiếp tục (Resume)...")
                await self._pause_event.wait()
                if self._is_cancelled:
                    job.status = JobStatus.CANCELLED
                    self._notify_job(job)
                    return
                job.status = JobStatus.RUNNING
                self._notify_job(job)

            if job.total_cost_usd >= job.budget_limit_usd:
                job.status = JobStatus.FAILED
                job.error_message = (
                    f"Dừng công việc: Chi phí ước tính (${job.total_cost_usd:.4f}) đã vượt trần ngân sách (${job.budget_limit_usd:.2f})"
                )
                self._notify_job(job)
                self._log(job.job_id, "ERROR", job.error_message)
                raise BudgetExceededError(job.error_message)

            runnable_tasks = scheduler.get_runnable_tasks(job.job_id)
            current_all_tasks = self.state_store.get_tasks_for_job(job.job_id)

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
                return

            if not incomplete_tasks:
                self._log(job.job_id, "INFO", "Toàn bộ nhiệm vụ trong đồ thị DAG đã hoàn thành thành công.")
                break

            if not runnable_tasks:
                running = [t for t in current_all_tasks if t.status == TaskStatus.RUNNING]
                if not running:
                    job.status = JobStatus.FAILED
                    job.error_message = "Không có nhiệm vụ nào sẵn sàng chạy mặc dù vẫn còn nhiệm vụ chưa hoàn tất (Bế tắc phụ thuộc)."
                    self._notify_job(job)
                    self._log(job.job_id, "ERROR", job.error_message)
                    return
                await asyncio.sleep(0.3)
                continue

            async def _worker(task_item: Task) -> Task:
                return await scheduler.execute_task_with_retry(
                    task=task_item,
                    executor_fn=lambda t: self._execute_task_logic(t, job),
                    max_retries=job.max_retries
                )

            results = await asyncio.gather(*[_worker(t) for t in runnable_tasks], return_exceptions=True)

            for r in results:
                if isinstance(r, Task):
                    job.total_tokens += r.usage.total_tokens
                    job.total_cost_usd += r.usage.estimated_cost_usd
                    self._notify_task(r)
                elif isinstance(r, Exception):
                    logger.error(f"Task batch exception: {r}")

            self._notify_job(job)

    async def _run_synthesis_stage(self, job: Job, planner_prov: str, planner_mod: str) -> list[str]:
        """Stage 4: Synthesize drafted sections and output publication documents."""
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

        synth_task.status = TaskStatus.SUCCEEDED
        synth_task.output_content = f"Đã xuất bản thành công {len(generated_files)} tệp: {', '.join(Path(f).name for f in generated_files)}"
        self._notify_task(synth_task)

        return generated_files

    async def run_job(
        self,
        job: Job,
        default_provider: str = "omniroute",
        default_model: str = "auto",
        planner_provider: Optional[str] = None,
        planner_model: Optional[str] = None,
        writer_provider: Optional[str] = None,
        writer_model: Optional[str] = None,
        reviewer_provider: Optional[str] = None,
        reviewer_model: Optional[str] = None,
    ) -> Job:
        """Execute complete lifecycle of a Job through separated business stages."""
        self._is_paused = False
        self._is_cancelled = False
        self._pause_event.set()

        planner_prov, planner_mod, writer_prov, writer_mod, rev_prov, rev_mod = self._resolve_routing(
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
        self._reviewer_prov = rev_prov
        self._reviewer_mod = rev_mod

        try:
            # Stage 1: Planning Phase
            if not job.plan:
                await self._run_planning_stage(job, planner_prov, planner_mod, writer_prov, writer_mod)

            # Stage 2: Research Phase
            await self._run_research_stage(job)

            # Stage 3: Task Execution Loop via DAG Scheduler
            scheduler = DAGScheduler(self.state_store, max_concurrency=job.max_concurrency)
            await self._run_execution_stage(job, scheduler)

            if job.status in (JobStatus.CANCELLED, JobStatus.FAILED):
                return job

            # Stage 4: Synthesis & Document Building Phase
            generated_files = await self._run_synthesis_stage(job, planner_prov, planner_mod)
            job.generated_files = generated_files
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
        """Internal business logic for executing a single task with targeted quality verification."""
        if task.role == TaskRole.RESEARCHER:
            refs = await self.researcher.research_for_job(job.job_id, [task.input.get("instructions", "")])
            task.output_content = f"Đã tra cứu {len(refs)} tài liệu tham chiếu."
            return task

        # WRITER execution with targeted repair (No redundant multi-round AI debate)
        accumulated_context = ""
        all_tasks = self.state_store.get_tasks_for_job(job.job_id)
        for prev in all_tasks:
            if prev.task_id != task.task_id and prev.status == TaskStatus.SUCCEEDED and prev.output_content and prev.task_id not in ("T-PLANNER", "T-FINAL"):
                accumulated_context += f"\n\n### {prev.input.get('title', '')}\n{prev.output_content}"

        critiques_to_fix: list[str] = []
        max_repairs = settings.max_review_rounds

        for attempt in range(max_repairs + 1):
            # Step 1: Draft section via Cloud AI (OmniRoute Gateway)
            draft, usage = await self.writer.draft_section(
                task=task,
                previous_context=accumulated_context,
                critiques_to_fix=critiques_to_fix if critiques_to_fix else None,
                dry_run=job.dry_run
            )
            task.output_content = draft
            task.usage.prompt_tokens += usage.prompt_tokens
            task.usage.completion_tokens += usage.completion_tokens
            task.usage.total_tokens += usage.total_tokens
            task.usage.estimated_cost_usd += usage.estimated_cost_usd

            # Step 2: Deterministic Code Validation (Zero AI review overhead)
            defects = self.validator.check_section_defects(draft)

            # In dry_run or mock testing, ensure mock reviewer compatibility
            if job.dry_run and not defects:
                rev_prov = getattr(self, "_reviewer_prov", task.provider)
                rev_model = getattr(self, "_reviewer_mod", task.model)
                review_res, rev_usage = await self.reviewer.review_section(
                    task=task,
                    content=draft,
                    provider=rev_prov,
                    model=rev_model,
                    dry_run=True
                )
                task.review_result = review_res
                task.usage.prompt_tokens += rev_usage.prompt_tokens
                task.usage.completion_tokens += rev_usage.completion_tokens
                task.usage.total_tokens += rev_usage.total_tokens
                task.usage.estimated_cost_usd += rev_usage.estimated_cost_usd
                self._log(
                    job.job_id, "INFO",
                    f"Nhiệm vụ [{task.task_id}] kiểm tra hợp lệ (Mô phỏng đạt chuẩn {review_res.score:.1f}/10).",
                    task_id=task.task_id
                )
                break

            if not defects:
                # No defects detected by code: approve immediately!
                task.review_result = ReviewResult(
                    is_approved=True,
                    score=9.5,
                    critiques=[],
                    summary="Đạt chuẩn cấu trúc qua kiểm định tự động."
                )
                self._log(
                    job.job_id, "INFO",
                    f"Nhiệm vụ [{task.task_id}] đạt chuẩn cấu trúc (Code kiểm tra tự động không phát hiện lỗi).",
                    task_id=task.task_id
                )
                break
            else:
                # Defects detected: targeted single-pass repair
                if attempt < max_repairs:
                    critiques_to_fix = [f"[CRITICAL] {d}" for d in defects]
                    self._log(
                        job.job_id, "WARN",
                        f"Nhiệm vụ [{task.task_id}] phát hiện lỗi: {', '.join(defects)}. Kích hoạt sửa chữa mục tiêu...",
                        task_id=task.task_id
                    )
                else:
                    task.review_result = ReviewResult(
                        is_approved=True,
                        score=7.0,
                        critiques=[],
                        summary=f"Chấp thuận bản tốt nhất sau sửa chữa. Cảnh báo còn lại: {', '.join(defects)}"
                    )
                    self._log(
                        job.job_id, "WARN",
                        f"Nhiệm vụ [{task.task_id}] hoàn thành sửa chữa với cảnh báo: {', '.join(defects)}",
                        task_id=task.task_id
                    )
                    break

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

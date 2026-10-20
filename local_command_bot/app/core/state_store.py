"""SQLite State Store for Job Lifecycle, Task Persistence, and Crash Recovery."""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Any
from datetime import datetime

from app.core.models import (
    Job, Task, JobStatus, TaskStatus, JobPlan,
    TokenUsage, ReviewResult, SourceReference, utc_now
)
from app.security.sanitizer import mask_secrets

logger = logging.getLogger(__name__)


class StateStore:
    """Persistent SQLite store for Jobs, Tasks, and Audit Logs."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a connection with WAL enabled and row factory."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """Initialize database schema tables if not present."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    status TEXT NOT NULL,
                    plan_json TEXT,
                    output_formats TEXT NOT NULL,
                    output_dir TEXT NOT NULL,
                    budget_limit_usd REAL NOT NULL,
                    total_cost_usd REAL NOT NULL DEFAULT 0.0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    max_concurrency INTEGER NOT NULL DEFAULT 3,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    timeout_seconds REAL NOT NULL DEFAULT 90.0,
                    dry_run INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    generated_files TEXT,
                    error_message TEXT
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_json TEXT,
                    dependencies_json TEXT,
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    output_path TEXT,
                    output_content TEXT,
                    error_message TEXT,
                    usage_json TEXT,
                    review_result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (job_id, task_id),
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS job_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    task_id TEXT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS source_references (
                    reference_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    issuing_body TEXT,
                    doc_number TEXT,
                    doc_type TEXT,
                    issue_date TEXT,
                    url TEXT,
                    status TEXT NOT NULL,
                    clause_used TEXT,
                    is_mandatory INTEGER NOT NULL DEFAULT 1,
                    verified_at TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_job_status ON tasks(job_id, status);
                CREATE INDEX IF NOT EXISTS idx_logs_job ON job_logs(job_id, id);
            """)

    # -------------------------------------------------------------
    # Job CRUD
    # -------------------------------------------------------------
    def save_job(self, job: Job) -> None:
        """Insert or update a Job record atomically."""
        job.updated_at = utc_now()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO jobs (
                    job_id, prompt, status, plan_json, output_formats, output_dir,
                    budget_limit_usd, total_cost_usd, total_tokens, max_concurrency,
                    max_retries, timeout_seconds, dry_run, created_at, updated_at,
                    completed_at, generated_files, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    prompt = excluded.prompt,
                    status = excluded.status,
                    plan_json = excluded.plan_json,
                    output_formats = excluded.output_formats,
                    output_dir = excluded.output_dir,
                    budget_limit_usd = excluded.budget_limit_usd,
                    total_cost_usd = excluded.total_cost_usd,
                    total_tokens = excluded.total_tokens,
                    max_concurrency = excluded.max_concurrency,
                    max_retries = excluded.max_retries,
                    timeout_seconds = excluded.timeout_seconds,
                    dry_run = excluded.dry_run,
                    updated_at = excluded.updated_at,
                    completed_at = excluded.completed_at,
                    generated_files = excluded.generated_files,
                    error_message = excluded.error_message
            """, (
                job.job_id,
                job.prompt,
                job.status.value,
                job.plan.model_dump_json() if job.plan else None,
                json.dumps([f.value for f in job.output_formats]),
                job.output_dir,
                job.budget_limit_usd,
                job.total_cost_usd,
                job.total_tokens,
                job.max_concurrency,
                job.max_retries,
                job.timeout_seconds,
                1 if job.dry_run else 0,
                job.created_at.isoformat(),
                job.updated_at.isoformat(),
                job.completed_at.isoformat() if job.completed_at else None,
                json.dumps(job.generated_files),
                job.error_message
            ))

    def get_job(self, job_id: str) -> Optional[Job]:
        """Fetch a single Job by ID."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    def list_jobs(self, limit: int = 50) -> list[Job]:
        """List recently created jobs."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._row_to_job(r) for r in rows]

    def _row_to_job(self, row: sqlite3.Row) -> Job:
        """Convert a database row into a Job instance."""
        plan_data = json.loads(row["plan_json"]) if row["plan_json"] else None
        plan = JobPlan.model_validate(plan_data) if plan_data else None

        formats = [f for f in json.loads(row["output_formats"])]
        gen_files = json.loads(row["generated_files"]) if row["generated_files"] else []

        return Job(
            job_id=row["job_id"],
            prompt=row["prompt"],
            status=JobStatus(row["status"]),
            plan=plan,
            output_formats=formats,
            output_dir=row["output_dir"],
            budget_limit_usd=row["budget_limit_usd"],
            total_cost_usd=row["total_cost_usd"],
            total_tokens=row["total_tokens"],
            max_concurrency=row["max_concurrency"],
            max_retries=row["max_retries"],
            timeout_seconds=row["timeout_seconds"],
            dry_run=bool(row["dry_run"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            generated_files=gen_files,
            error_message=row["error_message"]
        )

    # -------------------------------------------------------------
    # Task CRUD
    # -------------------------------------------------------------
    def save_task(self, task: Task) -> None:
        """Insert or update a Task record atomically."""
        task.updated_at = utc_now()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO tasks (
                    task_id, job_id, role, provider, model, input_json,
                    dependencies_json, status, attempt_count, max_attempts,
                    output_path, output_content, error_message, usage_json,
                    review_result_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id, task_id) DO UPDATE SET
                    role = excluded.role,
                    provider = excluded.provider,
                    model = excluded.model,
                    input_json = excluded.input_json,
                    dependencies_json = excluded.dependencies_json,
                    status = excluded.status,
                    attempt_count = excluded.attempt_count,
                    max_attempts = excluded.max_attempts,
                    output_path = excluded.output_path,
                    output_content = excluded.output_content,
                    error_message = excluded.error_message,
                    usage_json = excluded.usage_json,
                    review_result_json = excluded.review_result_json,
                    updated_at = excluded.updated_at
            """, (
                task.task_id,
                task.job_id,
                task.role.value,
                task.provider,
                task.model,
                json.dumps(task.input),
                json.dumps(task.dependencies),
                task.status.value,
                task.attempt_count,
                task.max_attempts,
                task.output_path,
                task.output_content,
                task.error_message,
                task.usage.model_dump_json(),
                task.review_result.model_dump_json() if task.review_result else None,
                task.created_at.isoformat(),
                task.updated_at.isoformat()
            ))

    def get_task(self, job_id: str, task_id: str) -> Optional[Task]:
        """Fetch a specific Task by job_id and task_id."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE job_id = ? AND task_id = ?",
                (job_id, task_id)
            ).fetchone()
            if not row:
                return None
            return self._row_to_task(row)

    def get_tasks_for_job(self, job_id: str) -> list[Task]:
        """Fetch all tasks belonging to a job, ordered by created_at."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE job_id = ? ORDER BY rowid ASC",
                (job_id,)
            ).fetchall()
            return [self._row_to_task(r) for r in rows]

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert a database row into a Task instance."""
        usage_data = json.loads(row["usage_json"]) if row["usage_json"] else {}
        review_data = json.loads(row["review_result_json"]) if row["review_result_json"] else None

        return Task(
            task_id=row["task_id"],
            job_id=row["job_id"],
            role=row["role"],
            provider=row["provider"],
            model=row["model"],
            input=json.loads(row["input_json"]) if row["input_json"] else {},
            dependencies=json.loads(row["dependencies_json"]) if row["dependencies_json"] else [],
            status=TaskStatus(row["status"]),
            attempt_count=row["attempt_count"],
            max_attempts=row["max_attempts"],
            output_path=row["output_path"],
            output_content=row["output_content"],
            error_message=row["error_message"],
            usage=TokenUsage.model_validate(usage_data),
            review_result=ReviewResult.model_validate(review_data) if review_data else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )

    # -------------------------------------------------------------
    # Logging and Audit Trail
    # -------------------------------------------------------------
    def append_log(self, job_id: str, level: str, message: str, task_id: Optional[str] = None) -> None:
        """Append a masked log line to the SQLite job audit trail."""
        safe_message = mask_secrets(message)
        now_str = utc_now().isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO job_logs (job_id, task_id, timestamp, level, message)
                VALUES (?, ?, ?, ?, ?)
            """, (job_id, task_id, now_str, level.upper(), safe_message))

    def get_logs(self, job_id: str, limit: int = 200) -> list[dict[str, Any]]:
        """Fetch chronological log records for a job."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT task_id, timestamp, level, message
                FROM job_logs WHERE job_id = ? ORDER BY id ASC LIMIT ?
            """, (job_id, limit)).fetchall()
            return [dict(r) for r in rows]

    # -------------------------------------------------------------
    # Source Reference Tracking
    # -------------------------------------------------------------
    def save_source_reference(self, ref: SourceReference) -> None:
        """Save legal or technical reference."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO source_references (
                    reference_id, job_id, title, issuing_body, doc_number,
                    doc_type, issue_date, url, status, clause_used, is_mandatory, verified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(reference_id) DO UPDATE SET
                    title = excluded.title,
                    issuing_body = excluded.issuing_body,
                    doc_number = excluded.doc_number,
                    status = excluded.status,
                    clause_used = excluded.clause_used,
                    url = excluded.url,
                    verified_at = excluded.verified_at
            """, (
                ref.reference_id,
                ref.job_id,
                ref.title,
                ref.issuing_body,
                ref.doc_number,
                ref.doc_type,
                ref.issue_date,
                ref.url,
                ref.status,
                ref.clause_used,
                1 if ref.is_mandatory else 0,
                ref.verified_at.isoformat() if ref.verified_at else None
            ))

    def get_source_references(self, job_id: str) -> list[SourceReference]:
        """Fetch all references linked to a job."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM source_references WHERE job_id = ?", (job_id,)
            ).fetchall()
            refs = []
            for r in rows:
                refs.append(SourceReference(
                    reference_id=r["reference_id"],
                    job_id=r["job_id"],
                    title=r["title"],
                    issuing_body=r["issuing_body"] or "",
                    doc_number=r["doc_number"],
                    doc_type=r["doc_type"] or "",
                    issue_date=r["issue_date"],
                    url=r["url"],
                    status=r["status"],
                    clause_used=r["clause_used"],
                    is_mandatory=bool(r["is_mandatory"]),
                    verified_at=datetime.fromisoformat(r["verified_at"]) if r["verified_at"] else None
                ))
            return refs

    # -------------------------------------------------------------
    # Crash Recovery
    # -------------------------------------------------------------
    def recover_interrupted_jobs(self) -> list[Job]:
        """Detect jobs that were left in RUNNING or PLANNING state and mark them for resumption."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM jobs WHERE status IN ('RUNNING', 'PLANNING')
            """).fetchall()
            recovered = []
            for r in rows:
                job = self._row_to_job(r)
                # Set status to PAUSED so user can safely review and resume
                job.status = JobStatus.PAUSED
                self.save_job(job)
                self.append_log(
                    job.job_id, "WARN",
                    "Khôi phục phiên làm việc sau khi ứng dụng bị gián đoạn đột ngột. Trạng thái chuyển sang PAUSED."
                )
                recovered.append(job)
            return recovered

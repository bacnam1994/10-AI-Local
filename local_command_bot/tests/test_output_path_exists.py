"""Test 18: Verifies generated output files physically exist on disk and are non-empty."""

import pytest
from pathlib import Path
from app.core.models import Job, OutputFormat, JobStatus
from app.core.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_output_files_exist_and_non_empty(temp_db, temp_output_dir):
    orch = Orchestrator(state_store=temp_db)

    job = Job(
        job_id="disk_check_job",
        prompt="Sample requirement",
        output_dir=str(temp_output_dir),
        output_formats=[OutputFormat.DOCX, OutputFormat.PDF, OutputFormat.MD],
        dry_run=True
    )
    temp_db.save_job(job)

    finished_job = await orch.run_job(job, default_provider="mock", default_model="mock-model")

    assert finished_job.status == JobStatus.SUCCEEDED
    assert len(finished_job.generated_files) == 3

    for file_path_str in finished_job.generated_files:
        p = Path(file_path_str)
        assert p.exists(), f"File {file_path_str} was declared but does not exist on disk"
        assert p.is_file()
        assert p.stat().st_size > 0, f"File {file_path_str} is unexpectedly empty"

"""Test 17: SOP draft generation with mandatory DRAFT disclaimer and GMP compliance."""

import pytest
from app.core.models import Job, OutputFormat, JobStatus
from app.core.job_manager import JobManager
from app.core.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_sop_draft_generation_pipeline(temp_db, temp_output_dir):
    orch = Orchestrator(state_store=temp_db)

    job = Job(
        job_id="sop_sample_pipeline",
        prompt=(
            "Soạn thảo SOP Vệ sinh phòng sạch cấp D theo Thông tư 35/2018/TT-BYT GMP-WHO."
        ),
        output_dir=str(temp_output_dir),
        output_formats=[OutputFormat.DOCX, OutputFormat.MD],
        dry_run=True  # deterministic mock execution
    )
    temp_db.save_job(job)

    finished_job = await orch.run_job(job, default_provider="mock", default_model="mock-model")

    assert finished_job.status == JobStatus.SUCCEEDED
    assert len(finished_job.generated_files) >= 2

    # Verify generated markdown file contains draft disclaimer
    md_file = [f for f in finished_job.generated_files if f.endswith(".md")][0]
    with open(md_file, "r", encoding="utf-8") as f:
        md_text = f.read()

    assert "DRAFT — CHỜ RÀ SOÁT VÀ PHÊ DUYỆT" in md_text
    assert "Thông tư 35/2018/TT-BYT" in md_text

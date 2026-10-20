"""Test Streamlined Pipeline: Local AI (Ollama) -> Cloud AI (OmniRoute) -> DOCX."""

import pytest
from pathlib import Path
from docx import Document

from app.core.models import Job, OutputFormat, JobStatus, TaskRole
from app.core.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_streamlined_pipeline_ollama_omniroute_docx(temp_db, temp_output_dir):
    """Verify that the streamlined workflow produces a valid DOCX file without redundant debate loops."""
    orch = Orchestrator(state_store=temp_db)

    # 1. User Prompt (Requirements)
    prompt = (
        "Soạn thảo Quy trình Thao tác Chuẩn (SOP) về 'Vệ sinh và Khử trùng Phòng sạch cấp D' "
        "cho phân xưởng sản xuất thuốc vô trùng theo Thông tư 35/2018/TT-BYT và Dược điển Việt Nam V."
    )

    job = Job(
        job_id="streamlined_job_001",
        prompt=prompt,
        output_dir=str(temp_output_dir),
        output_formats=[OutputFormat.DOCX],
        dry_run=True  # Uses MockAdapter for offline test
    )
    temp_db.save_job(job)

    # 2. Run Job via Orchestrator with streamlined defaults
    finished_job = await orch.run_job(
        job=job,
        default_provider="mock",
        planner_provider="mock",
        planner_model="mock-ollama-llama3.1",
        writer_provider="mock",
        writer_model="mock-omniroute-auto",
    )

    # 3. Assert Job Succeeded
    assert finished_job.status == JobStatus.SUCCEEDED
    assert len(finished_job.generated_files) == 1

    docx_path = Path(finished_job.generated_files[0])
    assert docx_path.exists()
    assert docx_path.suffix == ".docx"
    assert docx_path.stat().st_size > 1000

    # 4. Verify Document Content
    doc = Document(str(docx_path))
    full_text = "\n".join([p.text for p in doc.paragraphs])

    # Check mandatory GMP disclaimer
    assert "DRAFT" in full_text
    assert "CHỜ RÀ SOÁT VÀ PHÊ DUYỆT" in full_text

    # 5. Verify tasks in StateStore
    tasks = temp_db.get_tasks_for_job(job.job_id)
    task_map = {t.task_id: t for t in tasks}

    # Verify Planner task
    assert "T-PLANNER" in task_map
    assert task_map["T-PLANNER"].status == JobStatus.SUCCEEDED
    assert task_map["T-PLANNER"].model == "mock-ollama-llama3.1"

    # Verify Writer tasks have targeted review approval without excessive retries
    writer_tasks = [t for t in tasks if t.role == TaskRole.WRITER]
    assert len(writer_tasks) > 0
    for wt in writer_tasks:
        assert wt.status == JobStatus.SUCCEEDED
        assert wt.model == "mock-omniroute-auto"
        assert wt.review_result is not None
        assert wt.review_result.is_approved is True

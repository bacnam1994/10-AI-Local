"""Test 12: Content merging preserves section integrity and ordering."""

import pytest
from app.core.models import Job, Task, TaskRole, TaskStatus, OutputFormat
from app.document.md_builder import MarkdownBuilder


def test_content_merge_preserves_order(temp_output_dir):
    builder = MarkdownBuilder()
    job = Job(
        job_id="merge_job_1",
        prompt="SOP test",
        output_dir=str(temp_output_dir),
        output_formats=[OutputFormat.MD]
    )

    sections = [
        ("Mục 1: Mục đích và Phạm vi", "Nội dung phần 1 về mục đích áp dụng."),
        ("Mục 2: Trách nhiệm", "Nội dung phần 2 về ma trận trách nhiệm RACI."),
        ("Mục 3: Quy trình Thực hiện", "Nội dung phần 3 các bước vệ sinh chi tiết."),
        ("Mục 4: Hồ sơ và Biểu mẫu", "Nội dung phần 4 về lưu trữ nhật ký.")
    ]

    out_file = temp_output_dir / "merged_output.md"
    builder.build(job=job, sections=sections, references=[], output_file=out_file)

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")

    # Verify all 4 section headings exist
    for title, body in sections:
        assert title in content
        assert body in content

    # Verify sequential appearance order
    pos1 = content.find("Mục 1")
    pos2 = content.find("Mục 2")
    pos3 = content.find("Mục 3")
    pos4 = content.find("Mục 4")
    assert pos1 < pos2 < pos3 < pos4

"""Test 16: Guard against accidental file overwrite and path traversal attacks."""

import pytest
from pathlib import Path
from app.security.sanitizer import resolve_safe_output_path, validate_path_traversal


def test_no_overwrite_guard_appends_version(temp_output_dir):
    filename = "report.docx"
    file_v0 = temp_output_dir / filename
    file_v0.write_text("Original content", encoding="utf-8")

    # When allow_overwrite is False, it must not overwrite file_v0
    dest_path_1 = resolve_safe_output_path(temp_output_dir, filename, allow_overwrite=False)
    assert dest_path_1 != file_v0
    assert dest_path_1.name == "report_v1.docx"

    # Create report_v1.docx as well
    dest_path_1.write_text("Version 1 content", encoding="utf-8")

    # Next attempt should produce report_v2.docx
    dest_path_2 = resolve_safe_output_path(temp_output_dir, filename, allow_overwrite=False)
    assert dest_path_2.name == "report_v2.docx"


def test_path_traversal_detection(temp_output_dir):
    dangerous_path = temp_output_dir / ".." / "system_file.txt"
    with pytest.raises(PermissionError) as exc_info:
        validate_path_traversal(dangerous_path, temp_output_dir)
    assert "Security Violation" in str(exc_info.value)

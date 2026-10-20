"""Test 14: Document validation for placeholders and missing citations."""

import pytest
from app.document.validators import DocumentValidator


def test_validator_detects_placeholders():
    validator = DocumentValidator()
    text_with_placeholders = (
        "Quy trình được thực hiện bởi [Điền tên nhân viên ở đây] và người giám sát là <TBD>.\n"
        "Tham khảo [TODO] trước khi tiến hành.\n"
        "Trạng thái: DRAFT — CHỜ RÀ SOÁT VÀ PHÊ DUYỆT"
    )

    report = validator.validate(text_with_placeholders)
    assert not report.is_valid
    assert len(report.placeholders_found) >= 3
    assert any("Điền tên" in p for p in report.placeholders_found)
    assert any("TBD" in p for p in report.placeholders_found)


def test_validator_detects_missing_citations():
    validator = DocumentValidator()
    text_clean = (
        "Quy trình thao tác chuẩn vệ sinh phòng sạch cấp D.\n"
        "Trạng thái: DRAFT — CHỜ RÀ SOÁT VÀ PHÊ DUYỆT"
    )

    report = validator.validate(
        text_clean,
        mandatory_references=["Thông tư 35/2018/TT-BYT"]
    )
    assert "Thông tư 35/2018/TT-BYT" in report.missing_citations

"""Document Validators: Checks for placeholders, completeness, and missing citations."""

import re
from typing import Any
from pydantic import BaseModel

PLACEHOLDER_PATTERNS = [
    re.compile(r"\[Điền\s+[^\]]+\]", re.IGNORECASE),
    re.compile(r"\[Cần\s+điền[^\]]*\]", re.IGNORECASE),
    re.compile(r"\[TBD\]", re.IGNORECASE),
    re.compile(r"\[TODO\]", re.IGNORECASE),
    re.compile(r"\[Chưa\s+xác\s+định\]", re.IGNORECASE),
    re.compile(r"<TBD>", re.IGNORECASE),
    re.compile(r"<TODO>", re.IGNORECASE),
    re.compile(r"\[Chèn\s+[^\]]+\]", re.IGNORECASE),
]


class ValidationReport(BaseModel):
    """Result of document quality validation."""
    is_valid: bool
    placeholders_found: list[str]
    missing_sections: list[str]
    missing_citations: list[str]
    warnings: list[str]


class DocumentValidator:
    """Validates synthesized document content before publication."""

    def check_section_defects(self, text: str) -> list[str]:
        """Fast code-based check for drafting defects (placeholders, empty text)."""
        defects = []
        if not text or len(text.strip()) < 30:
            defects.append("Nội dung quá ngắn hoặc chưa hoàn chỉnh (< 30 ký tự).")
            return defects
        for pattern in PLACEHOLDER_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                defects.append(f"Chứa placeholder chưa điền: {', '.join(matches)}")
        return defects

    def validate(
        self,
        full_text: str,
        expected_sections: list[str] | None = None,
        mandatory_references: list[str] | None = None,
    ) -> ValidationReport:
        placeholders_found: list[str] = []
        for pattern in PLACEHOLDER_PATTERNS:
            matches = pattern.findall(full_text)
            if matches:
                placeholders_found.extend(matches)

        # Check section presence
        missing_sections: list[str] = []
        if expected_sections:
            for sec in expected_sections:
                clean_sec = re.sub(r"^\d+[\.\)]\s*", "", sec).strip().lower()
                if clean_sec not in full_text.lower():
                    missing_sections.append(sec)

        # Check citation presence
        missing_citations: list[str] = []
        if mandatory_references:
            for ref in mandatory_references:
                # Key tokens from reference
                tokens = [w for w in ref.split() if "/" in w or w.isdigit() or len(w) > 4]
                if tokens and not any(t.lower() in full_text.lower() for t in tokens):
                    missing_citations.append(ref)

        warnings: list[str] = []
        if "DRAFT — CHỜ RÀ SOÁT VÀ PHÊ DUYỆT" not in full_text:
            warnings.append("Văn bản chưa gắn cờ cảnh báo bắt buộc: 'DRAFT — CHỜ RÀ SOÁT VÀ PHÊ DUYỆT'")

        is_valid = len(placeholders_found) == 0 and len(missing_sections) == 0

        return ValidationReport(
            is_valid=is_valid,
            placeholders_found=placeholders_found,
            missing_sections=missing_sections,
            missing_citations=missing_citations,
            warnings=warnings
        )


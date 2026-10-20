"""Markdown Document Builder: Exports clean, standardized Markdown files."""

from pathlib import Path
from app.core.models import Job, SourceReference


class MarkdownBuilder:
    """Exports synthesized document as a structured Markdown file."""

    def build(
        self,
        job: Job,
        sections: list[tuple[str, str]],
        references: list[SourceReference],
        output_file: Path,
        doc_code: str = "SOP-PROD-001",
        version: str = "1.0",
        effective_date: str = "2026-10-20",
        department: str = "Phòng Đảm bảo Chất lượng (QA)",
    ) -> Path:
        objective = job.plan.objective if job.plan else "QUY TRÌNH THAO TÁC CHUẨN (SOP)"

        content = []
        content.append(f"# {objective.upper()}")
        content.append(f"> **TRẠNG THÁI: DRAFT — CHỜ RÀ SOÁT VÀ PHÊ DUYỆT (CHƯA CÓ GIÁ TRỊ PHÁP LÝ CHÍNH THỨC)**\n")
        content.append("## THÔNG TIN TÀI LIỆU")
        content.append(f"- **Mã tài liệu:** `{doc_code}`")
        content.append(f"- **Phiên bản:** `{version}` (Bản thảo sơ bộ)")
        content.append(f"- **Ngày dự thảo:** `{effective_date}`")
        content.append(f"- **Bộ phận soạn thảo:** {department}\n")
        content.append("## ĐIỀU PHỐI & PHÂN BỔ BỞI BOT CHỈ HUY LOCAL")
        content.append("- **AI Tổng Chỉ Huy (Commander & Planner):** Phân tích yêu cầu ban đầu, lập kế hoạch đồ thị DAG và nghiệm thu xuất bản.")
        content.append("- **AI Thợ Viết (Cloud Workers):** Soạn thảo chi tiết các phân đoạn SOP theo cấu trúc chuẩn.")
        content.append("- **AI Giám Sát (QA Reviewer):** Rà soát độc lập 8 tiêu chí chất lượng và vòng lặp phản hồi sửa đổi.\n")

        # Revision History
        content.append("## BẢNG LỊCH SỬ SỬA ĐỔI (REVISION HISTORY)")
        content.append("| Phiên bản | Ngày | Người thực hiện | Tóm tắt thay đổi |")
        content.append("|---|---|---|---|")
        content.append(f"| {version} | {effective_date} | AI Orchestrator | Khởi tạo bản thảo tự động theo yêu cầu |\n")

        # References
        if references:
            content.append("## DANH MỤC QUY CHUẨN & TÀI LIỆU THAM CHIẾU")
            content.append("| STT | Số hiệu / Tiêu đề | Cơ quan ban hành | Tình trạng hiệu lực |")
            content.append("|---|---|---|---|")
            for i, r in enumerate(references):
                num_str = f"{r.doc_number}: " if r.doc_number else ""
                content.append(f"| {i + 1} | {num_str}{r.title} | {r.issuing_body} | {r.status} |")
            content.append("\n")

        # Sections
        content.append("---")
        content.append("## NỘI DUNG CHI TIẾT\n")
        for title, md in sections:
            content.append(f"## {title}\n")
            content.append(md)
            content.append("\n")

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(content), encoding="utf-8")
        return output_file

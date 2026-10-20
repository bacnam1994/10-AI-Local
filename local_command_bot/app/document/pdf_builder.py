"""PDF Document Builder using ReportLab."""

import re
from pathlib import Path
from typing import Optional
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas

from app.core.models import Job, SourceReference


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and draw total page numbers and footers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#777777"))

        # Header
        self.drawRightString(A4[0] - 54, A4[1] - 36, "SOP-DRAFT | TỔNG CÔNG TY DƯỢC PHẨM VIỆT NAM")

        # Footer Notice
        self.setFillColor(colors.HexColor("#B71C1C"))
        self.drawCentredString(
            A4[0] / 2.0, 36,
            "TRẠNG THÁI: DRAFT — CHỜ RÀ SOÁT VÀ PHÊ DUYỆT (CHƯA CÓ GIÁ TRỊ PHÁP LÝ)"
        )

        # Page Number
        self.setFillColor(colors.HexColor("#555555"))
        page_str = f"Trang {self._pageNumber} / {page_count}"
        self.drawRightString(A4[0] - 54, 36, page_str)

        self.restoreState()


class PdfBuilder:
    """Builds formatted PDF documents using ReportLab."""

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
        output_file.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(output_file),
            pagesize=A4,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54,
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1A365D"),
            alignment=1,
            spaceAfter=10
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#4A5568"),
            alignment=1,
            spaceAfter=15
        )
        h1_style = ParagraphStyle(
            "Heading1_Custom",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#2B6CB0"),
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True
        )
        h2_style = ParagraphStyle(
            "Heading2_Custom",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#2D3748"),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True
        )
        body_style = ParagraphStyle(
            "Body_Custom",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#2D3748"),
            spaceAfter=6
        )

        story = []

        # Title Block
        story.append(Paragraph("TỔNG CÔNG TY DƯỢC PHẨM VIỆT NAM", subtitle_style))
        story.append(Paragraph(department.upper(), subtitle_style))
        objective = job.plan.objective if job.plan else "QUY TRÌNH THAO TÁC CHUẨN (SOP)"
        story.append(Paragraph(objective.upper(), title_style))

        draft_badge = Paragraph(
            "<b>[ DRAFT — CHỜ RÀ SOÁT VÀ PHÊ DUYỆT ]</b>",
            ParagraphStyle("DraftBadge", parent=subtitle_style, textColor=colors.HexColor("#C53030"))
        )
        story.append(draft_badge)
        story.append(Spacer(1, 10))

        # Metadata Table
        meta_data = [
            ["Mã tài liệu:", doc_code, "Phiên bản:", f"{version} (Bản thảo)"],
            ["Ngày hiệu lực:", effective_date, "Đơn vị:", department]
        ]
        meta_table = Table(meta_data, colWidths=[90, 150, 90, 150])
        meta_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2D3748")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 15))

        # References Table
        if references:
            story.append(Paragraph("Danh mục Quy chuẩn & Căn cứ Pháp lý", h2_style))
            ref_data = [["STT", "Số hiệu / Tiêu đề", "Cơ quan", "Tình trạng"]]
            for i, r in enumerate(references):
                ref_data.append([
                    str(i + 1),
                    f"{r.doc_number + ': ' if r.doc_number else ''}{r.title[:45]}...",
                    r.issuing_body[:18],
                    r.status[:25]
                ])
            ref_table = Table(ref_data, colWidths=[25, 235, 110, 110])
            ref_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(ref_table)
            story.append(Spacer(1, 15))

        story.append(PageBreak())

        # Render sections
        for title, md in sections:
            story.append(Paragraph(title, h1_style))
            for line in md.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("### "):
                    story.append(Paragraph(stripped[4:], h2_style))
                elif stripped.startswith("- ") or stripped.startswith("* "):
                    story.append(Paragraph(f"• {stripped[2:]}", body_style))
                elif not stripped.startswith("|"):
                    story.append(Paragraph(stripped, body_style))

            story.append(Spacer(1, 8))

        doc.build(story, canvasmaker=NumberedCanvas)
        return output_file

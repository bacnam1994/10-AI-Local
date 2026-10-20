"""Main Application Window for Local Command Bot."""

import os
import asyncio
import subprocess
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QPlainTextEdit, QCheckBox, QComboBox,
    QSpinBox, QDoubleSpinBox, QFileDialog, QProgressBar, QMessageBox,
    QGroupBox, QFrame, QScrollArea, QTabWidget
)
from PySide6.QtCore import Qt, QThread, Signal

from app.core.models import Job, Task, JobStatus, TaskStatus, OutputFormat
from app.core.job_manager import JobManager
from app.config.settings import settings
from app.ui.theme import DARK_STYLESHEET, STATUS_COLORS
from app.ui.components.task_table import TaskTableWidget
from app.ui.components.log_viewer import LogViewer
from app.ui.components.config_dialog import ConfigDialog

SAMPLE_GMP_PROMPT = (
    "Hãy soạn thảo một Quy trình Thao tác Chuẩn (SOP) hoàn chỉnh về 'Vệ sinh và Khử trùng Phòng sạch cấp D' "
    "cho phân xưởng sản xuất thuốc nhỏ mắt vô trùng, tuân thủ nghiêm ngặt theo tiêu chuẩn GMP-WHO (Thông tư 35/2018/TT-BYT) "
    "và Dược điển Việt Nam V. Tài liệu cần đầy đủ: Mục đích, Phạm vi áp dụng, Ma trận trách nhiệm, "
    "Thiết bị dụng cụ và nồng độ hóa chất khử trùng (cồn 70%, clo hoạt tính), Quy trình vệ sinh từng bước chi tiết "
    "(nguyên tắc từ trên xuống dưới, từ trong ra ngoài), Tần suất lấy mẫu giám sát vi sinh bề mặt, và Biểu mẫu nhật ký theo dõi."
)


class JobExecutionWorker(QThread):
    """Executes Orchestrator Job in a background QThread with an asyncio event loop."""
    job_updated = Signal(object)
    task_updated = Signal(object)
    log_received = Signal(str, str, object)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        job_manager: JobManager,
        job_id: str,
        provider: str,
        model: str,
        planner_provider: Optional[str] = None,
        planner_model: Optional[str] = None,
        writer_provider: Optional[str] = None,
        writer_model: Optional[str] = None,
        reviewer_provider: Optional[str] = None,
        reviewer_model: Optional[str] = None,
    ):
        super().__init__()
        self.job_manager = job_manager
        self.job_id = job_id
        self.provider = provider
        self.model = model
        self.planner_provider = planner_provider
        self.planner_model = planner_model
        self.writer_provider = writer_provider
        self.writer_model = writer_model
        self.reviewer_provider = reviewer_provider
        self.reviewer_model = reviewer_model

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Wire callbacks to emit Qt signals thread-safely
            self.job_manager.on_job_updated = lambda job: self.job_updated.emit(job)
            self.job_manager.on_task_updated = lambda task: self.task_updated.emit(task)
            self.job_manager.on_log = lambda lvl, msg, tid: self.log_received.emit(lvl, msg, tid)

            job = loop.run_until_complete(
                self.job_manager.start_job(
                    job_id=self.job_id,
                    default_provider=self.provider,
                    default_model=self.model,
                    planner_provider=self.planner_provider,
                    planner_model=self.planner_model,
                    writer_provider=self.writer_provider,
                    writer_model=self.writer_model,
                    reviewer_provider=self.reviewer_provider,
                    reviewer_model=self.reviewer_model,
                )
            )
            self.finished.emit(job)
        except Exception as e:
            self.failed.emit(str(e))
        finally:
            loop.close()


class MainWindow(QMainWindow):
    """Main Desktop UI Window for Local Command Bot."""

    def __init__(self, job_manager: Optional[JobManager] = None):
        super().__init__()
        self.setWindowTitle("Local Command Bot — Multi-Cloud AI Document Orchestrator")
        self.resize(1280, 850)
        self.setStyleSheet(DARK_STYLESHEET)

        self.job_manager = job_manager or JobManager()
        self.current_job: Optional[Job] = None
        self.worker: Optional[JobExecutionWorker] = None

        self._init_ui()
        self._check_crash_recovery()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # 1. Top Header & Control Bar
        header_bar = self._create_header_bar()
        main_layout.addWidget(header_bar)

        # 2. Main Splitter (Left: Controls & Input, Right: Progress & Logs)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)

        left_panel = self._create_left_input_panel()
        right_panel = self._create_right_monitoring_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        main_layout.addWidget(splitter)

        # 3. Bottom Status and Output Banner
        self.status_banner = self._create_status_banner()
        main_layout.addWidget(self.status_banner)

    def _create_header_bar(self) -> QWidget:
        header = QFrame()
        header.setObjectName("card")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(10, 8, 10, 8)

        # App Brand
        title_box = QVBoxLayout()
        title_label = QLabel("COMMAND BOT: AI DOCUMENT ORCHESTRATOR")
        title_label.setObjectName("headerTitle")
        sub_label = QLabel("Tự động hóa lập kế hoạch, phân bổ đa Cloud AI, kiểm soát chất lượng & xuất bản SOP/DOCX")
        sub_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        title_box.addWidget(title_label)
        title_box.addWidget(sub_label)
        layout.addLayout(title_box)

        layout.addStretch()

        # Stats Cards
        self.stat_status = QLabel("SẴN SÀNG")
        self.stat_status.setStyleSheet("color: #10B981; font-weight: bold;")
        self.stat_cost = QLabel("$0.0000")
        self.stat_cost.setObjectName("statValue")
        self.stat_tokens = QLabel("0")
        self.stat_tokens.setObjectName("statValue")

        layout.addWidget(self._stat_widget("TRẠNG THÁI", self.stat_status))
        layout.addWidget(self._stat_widget("CHI PHÍ", self.stat_cost))
        layout.addWidget(self._stat_widget("TOKENS", self.stat_tokens))

        # API Key Settings Button
        btn_settings = QPushButton("⚙ Cấu hình API Key")
        btn_settings.clicked.connect(self._open_settings)
        layout.addWidget(btn_settings)

        return header

    def _stat_widget(self, label: str, value_label: QLabel) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(6, 2, 6, 2)
        v.setSpacing(2)
        lbl = QLabel(label)
        lbl.setObjectName("statLabel")
        v.addWidget(lbl)
        v.addWidget(value_label)
        return w

    def _create_left_input_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(12)

        # Group 1: Natural Language Requirement
        req_group = QGroupBox("1. Yêu cầu Văn bản (Prompt dài)")
        req_layout = QVBoxLayout(req_group)

        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlaceholderText(
            "Nhập yêu cầu chi tiết bằng tiếng Việt hoặc tiếng Anh...\n"
            "Ví dụ: Soạn thảo SOP Vệ sinh phòng sạch cấp D tuân thủ Thông tư 35/2018/TT-BYT..."
        )
        self.prompt_edit.setMinimumHeight(150)
        req_layout.addWidget(self.prompt_edit)

        btn_sample = QPushButton("📋 Chèn Prompt SOP Mẫu")
        btn_sample.clicked.connect(lambda: self.prompt_edit.setPlainText(SAMPLE_GMP_PROMPT))
        req_layout.addWidget(btn_sample)

        layout.addWidget(req_group)

        # Group 2: Output Formats & Directory
        out_group = QGroupBox("2. Định dạng & Thư mục Đầu ra")
        out_layout = QVBoxLayout(out_group)

        fmt_layout = QHBoxLayout()
        self.cb_docx = QCheckBox("DOCX (Word)")
        self.cb_docx.setChecked(True)
        self.cb_pdf = QCheckBox("PDF (Bản in)")
        self.cb_pdf.setChecked(True)
        self.cb_md = QCheckBox("Markdown (Nguồn)")
        self.cb_md.setChecked(True)
        fmt_layout.addWidget(self.cb_docx)
        fmt_layout.addWidget(self.cb_pdf)
        fmt_layout.addWidget(self.cb_md)
        out_layout.addLayout(fmt_layout)

        dir_layout = QHBoxLayout()
        self.out_dir_label = QLabel(str(settings.outputs_dir))
        self.out_dir_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        btn_browse = QPushButton("Duyệt...")
        btn_browse.setMaximumWidth(75)
        btn_browse.clicked.connect(self._browse_output_dir)
        dir_layout.addWidget(self.out_dir_label)
        dir_layout.addWidget(btn_browse)
        out_layout.addLayout(dir_layout)

        layout.addWidget(out_group)

        # Group 3: AI Provider & Models Selection
        model_group = QGroupBox("3. Thiết lập AI Chỉ Huy & Phân Bổ Vai Trò")
        model_layout = QVBoxLayout(model_group)

        # Basic Single Provider Row
        row_prov = QHBoxLayout()
        row_prov.addWidget(QLabel("Nhà cung cấp chung:"))
        self.combo_provider = QComboBox()
        self.combo_provider.addItems([
            "openai", "anthropic", "gemini", "groq", "openrouter", "deepseek", "ollama", "custom", "mock"
        ])
        self.combo_provider.currentIndexChanged.connect(self._on_provider_changed)
        row_prov.addWidget(self.combo_provider)
        model_layout.addLayout(row_prov)

        row_model = QHBoxLayout()
        row_model.addWidget(QLabel("Mô hình chung (Model):"))
        self.combo_model = QComboBox()
        self.combo_model.addItems(["gpt-4o-mini", "gpt-4o"])
        row_model.addWidget(self.combo_model)
        model_layout.addLayout(row_model)

        # Multi-Agent Role Assignment Toggle
        self.cb_multi_agent = QCheckBox("🎖️ Bật Phân Vai Đa AI (Tổng Chỉ Huy vs Cloud Worker vs Giám Sát)")
        self.cb_multi_agent.setStyleSheet("color: #38BDF8; font-weight: bold; margin-top: 6px;")
        model_layout.addWidget(self.cb_multi_agent)

        # Multi-Agent Role Frame
        self.frame_multi_agent = QFrame()
        self.frame_multi_agent.setStyleSheet(
            "background-color: #0F172A; border: 1px solid #334155; border-radius: 6px; padding: 6px;"
        )
        ma_layout = QVBoxLayout(self.frame_multi_agent)
        ma_layout.setContentsMargins(8, 8, 8, 8)
        ma_layout.setSpacing(6)

        # 1. Commander AI
        lbl_cmd = QLabel("🎖️ AI Tổng Chỉ Huy (Lập kế hoạch DAG & Duyệt xuất bản):")
        lbl_cmd.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 11px;")
        ma_layout.addWidget(lbl_cmd)
        row_cmd = QHBoxLayout()
        self.combo_cmd_prov = QComboBox()
        self.combo_cmd_prov.addItems(["ollama", "groq", "openai", "anthropic", "gemini", "deepseek", "huggingface", "openrouter", "custom", "mock"])
        self.combo_cmd_model = QComboBox()
        self.combo_cmd_prov.currentIndexChanged.connect(lambda: self._populate_model_combo(self.combo_cmd_model, self.combo_cmd_prov.currentText()))
        self._populate_model_combo(self.combo_cmd_model, "ollama")
        row_cmd.addWidget(self.combo_cmd_prov, 4)
        row_cmd.addWidget(self.combo_cmd_model, 6)
        ma_layout.addLayout(row_cmd)

        # 2. Worker AI
        lbl_wrk = QLabel("✍️ AI Thợ Viết (Cloud AI soạn thảo chuyên mục song song):")
        lbl_wrk.setStyleSheet("color: #34D399; font-weight: bold; font-size: 11px;")
        ma_layout.addWidget(lbl_wrk)
        row_wrk = QHBoxLayout()
        self.combo_worker_prov = QComboBox()
        self.combo_worker_prov.addItems(["auto", "groq", "huggingface", "openai", "deepseek", "anthropic", "gemini", "ollama", "openrouter", "custom", "mock"])
        self.combo_worker_model = QComboBox()
        self.combo_worker_prov.currentIndexChanged.connect(lambda: self._populate_model_combo(self.combo_worker_model, self.combo_worker_prov.currentText()))
        self._populate_model_combo(self.combo_worker_model, "auto")
        row_wrk.addWidget(self.combo_worker_prov, 4)
        row_wrk.addWidget(self.combo_worker_model, 6)
        ma_layout.addLayout(row_wrk)

        # 3. Reviewer AI
        lbl_rev = QLabel("🔍 AI Giám Sát Chất Lượng (Rà soát 8 tiêu chí & bắt sửa):")
        lbl_rev.setStyleSheet("color: #FBBF24; font-weight: bold; font-size: 11px;")
        ma_layout.addWidget(lbl_rev)
        row_rev = QHBoxLayout()
        self.combo_rev_prov = QComboBox()
        self.combo_rev_prov.addItems(["ollama", "openai", "gemini", "anthropic", "groq", "deepseek", "huggingface", "openrouter", "custom", "mock"])
        self.combo_rev_model = QComboBox()
        self.combo_rev_prov.currentIndexChanged.connect(lambda: self._populate_model_combo(self.combo_rev_model, self.combo_rev_prov.currentText()))
        self._populate_model_combo(self.combo_rev_model, "ollama")
        row_rev.addWidget(self.combo_rev_prov, 4)
        row_rev.addWidget(self.combo_rev_model, 6)
        ma_layout.addLayout(row_rev)

        self.frame_multi_agent.setVisible(False)
        self.cb_multi_agent.toggled.connect(self.frame_multi_agent.setVisible)
        model_layout.addWidget(self.frame_multi_agent)

        # Dry Run Mode Checkbox
        self.cb_dry_run = QCheckBox("Chế độ Dry Run (Chạy giả lập kiểm tra DAG, không tốn token)")
        self.cb_dry_run.toggled.connect(self._on_dry_run_toggled)
        model_layout.addWidget(self.cb_dry_run)

        layout.addWidget(model_group)

        # Group 4: Operational Limits
        limits_group = QGroupBox("4. Giới hạn Ngân sách & Tiến trình")
        limits_layout = QVBoxLayout(limits_group)

        lim_row1 = QHBoxLayout()
        lim_row1.addWidget(QLabel("Trần chi phí ($ USD):"))
        self.spin_budget = QDoubleSpinBox()
        self.spin_budget.setRange(0.1, 100.0)
        self.spin_budget.setValue(settings.default_budget_limit_usd)
        lim_row1.addWidget(self.spin_budget)

        lim_row1.addWidget(QLabel("Tác vụ song song:"))
        self.spin_concurrency = QSpinBox()
        self.spin_concurrency.setRange(1, 10)
        self.spin_concurrency.setValue(settings.default_max_concurrency)
        lim_row1.addWidget(self.spin_concurrency)
        limits_layout.addLayout(lim_row1)

        lim_row2 = QHBoxLayout()
        lim_row2.addWidget(QLabel("Số lần thử lại (Retries):"))
        self.spin_retries = QSpinBox()
        self.spin_retries.setRange(0, 5)
        self.spin_retries.setValue(settings.default_max_retries)
        lim_row2.addWidget(self.spin_retries)

        lim_row2.addWidget(QLabel("Timeout (giây):"))
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(10, 600)
        self.spin_timeout.setValue(int(settings.default_timeout_seconds))
        lim_row2.addWidget(self.spin_timeout)
        limits_layout.addLayout(lim_row2)

        layout.addWidget(limits_group)

        # Group 5: Primary Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_start = QPushButton("▶ Bắt đầu (Start)")
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.setFixedHeight(38)
        self.btn_start.clicked.connect(self._start_job)

        self.btn_pause = QPushButton("⏸ Tạm dừng")
        self.btn_pause.setObjectName("warningButton")
        self.btn_pause.setFixedHeight(38)
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._pause_job)

        self.btn_resume = QPushButton("▶ Tiếp tục")
        self.btn_resume.setObjectName("successButton")
        self.btn_resume.setFixedHeight(38)
        self.btn_resume.setEnabled(False)
        self.btn_resume.clicked.connect(self._resume_job)

        self.btn_cancel = QPushButton("⏹ Hủy bỏ")
        self.btn_cancel.setObjectName("dangerButton")
        self.btn_cancel.setFixedHeight(38)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_job)

        btn_box.addWidget(self.btn_start)
        btn_box.addWidget(self.btn_pause)
        btn_box.addWidget(self.btn_resume)
        btn_box.addWidget(self.btn_cancel)

        layout.addLayout(btn_box)
        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _create_right_monitoring_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Overall Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Tabs for DAG Task Table and Live Logs
        tabs = QTabWidget()

        # Tab 1: DAG Task Progress Table
        self.task_table = TaskTableWidget()
        tabs.addTab(self.task_table, "Đồ thị Nhiệm vụ (DAG Tasks)")

        # Tab 2: Live Log Console
        self.log_viewer = LogViewer()
        tabs.addTab(self.log_viewer, "Nhật ký Chi tiết (Console Logs)")

        layout.addWidget(tabs)
        return container

    def _create_status_banner(self) -> QFrame:
        banner = QFrame()
        banner.setObjectName("card")
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(12, 8, 12, 8)

        self.banner_msg = QLabel("Chưa có phiên làm việc nào đang chạy. Nhập yêu cầu và nhấn 'Bắt đầu'.")
        self.banner_msg.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(self.banner_msg)

        layout.addStretch()

        self.btn_open_folder = QPushButton("📂 Mở Thư mục Kết quả")
        self.btn_open_folder.setObjectName("successButton")
        self.btn_open_folder.setVisible(False)
        self.btn_open_folder.clicked.connect(self._open_output_folder)
        layout.addWidget(self.btn_open_folder)

        self.btn_open_file = QPushButton("📄 Mở Tài liệu DOCX")
        self.btn_open_file.setVisible(False)
        self.btn_open_file.clicked.connect(self._open_output_file)
        layout.addWidget(self.btn_open_file)

        return banner

    # -------------------------------------------------------------
    # UI Event Handlers
    # -------------------------------------------------------------
    def _populate_model_combo(self, combo: QComboBox, prov: str):
        combo.clear()
        if prov == "openai":
            combo.setEditable(False)
            combo.addItems(["gpt-4o-mini", "gpt-4o"])
        elif prov == "anthropic":
            combo.setEditable(False)
            combo.addItems(["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"])
        elif prov == "gemini":
            combo.setEditable(False)
            combo.addItems(["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"])
        elif prov == "groq":
            combo.setEditable(True)
            combo.addItems([
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
                "gemma2-9b-it"
            ])
        elif prov == "deepseek":
            combo.setEditable(True)
            combo.addItems([
                "deepseek-chat",
                "deepseek-reasoner"
            ])
        elif prov == "ollama":
            combo.setEditable(True)
            combo.addItems([
                "llama3.1",
                "qwen2.5:14b",
                "deepseek-r1:8b",
                "mistral"
            ])
        elif prov == "openrouter":
            combo.setEditable(True)
            combo.addItems([
                "anthropic/claude-3.5-sonnet",
                "anthropic/claude-3.5-haiku",
                "openai/gpt-4o",
                "openai/gpt-4o-mini",
                "google/gemini-pro-1.5",
                "google/gemini-flash-1.5",
                "meta-llama/llama-3.1-70b-instruct",
                "deepseek/deepseek-chat",
                "qwen/qwen-2.5-72b-instruct"
            ])
        elif prov == "huggingface":
            combo.setEditable(True)
            combo.addItems([
                "mistralai/Mistral-7B-Instruct-v0.3",
                "meta-llama/Meta-Llama-3-70B-Instruct",
                "Qwen/Qwen2.5-72B-Instruct",
                "mistralai/Mixtral-8x7B-Instruct-v0.1"
            ])
        elif prov == "auto":
            combo.setEditable(False)
            combo.addItems(["auto-smart-routing (Local AI tự chọn Cloud AI tối ưu theo Task)"])
        elif prov == "custom":
            combo.setEditable(True)
            combo.addItems(["custom-model", "gpt-4o-mini", "llama3"])
        elif prov == "mock":
            combo.setEditable(False)
            combo.addItems(["mock-model", "mock-pro-model"])

    def _on_provider_changed(self, index: int):
        prov = self.combo_provider.currentText()
        self._populate_model_combo(self.combo_model, prov)

    def _on_dry_run_toggled(self, checked: bool):
        if checked:
            self.combo_provider.setCurrentText("mock")
        else:
            if self.combo_provider.currentText() == "mock":
                self.combo_provider.setCurrentText("openai")

    def _browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu kết quả", str(settings.outputs_dir))
        if folder:
            self.out_dir_label.setText(folder)

    def _open_settings(self):
        dlg = ConfigDialog(self)
        dlg.exec()

    def _start_job(self):
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập nội dung yêu cầu trước khi bắt đầu.")
            return

        # Output formats
        formats = []
        if self.cb_docx.isChecked():
            formats.append(OutputFormat.DOCX)
        if self.cb_pdf.isChecked():
            formats.append(OutputFormat.PDF)
        if self.cb_md.isChecked():
            formats.append(OutputFormat.MD)

        if not formats:
            QMessageBox.warning(self, "Thiếu định dạng", "Vui lòng chọn ít nhất một định dạng đầu ra (DOCX, PDF, hoặc Markdown).")
            return

        dry_run = self.cb_dry_run.isChecked()
        provider = self.combo_provider.currentText()
        model = self.combo_model.currentText()

        # Multi-Agent Role overrides
        if self.cb_multi_agent.isChecked() and not dry_run:
            planner_provider = self.combo_cmd_prov.currentText()
            planner_model = self.combo_cmd_model.currentText()
            writer_provider = self.combo_worker_prov.currentText()
            writer_model = self.combo_worker_model.currentText()
            reviewer_provider = self.combo_rev_prov.currentText()
            reviewer_model = self.combo_rev_model.currentText()
        else:
            planner_provider = provider
            planner_model = model
            writer_provider = provider
            writer_model = model
            reviewer_provider = provider
            reviewer_model = model

        # Create Job
        self.current_job = self.job_manager.create_job(
            prompt=prompt,
            output_formats=formats,
            output_dir=self.out_dir_label.text(),
            budget_limit_usd=self.spin_budget.value(),
            max_concurrency=self.spin_concurrency.value(),
            max_retries=self.spin_retries.value(),
            timeout_seconds=float(self.spin_timeout.value()),
            dry_run=dry_run
        )

        # Reset UI
        self.task_table.clear_tasks()
        self.log_viewer.clear_logs()
        self.progress_bar.setValue(5)
        self.btn_open_folder.setVisible(False)
        self.btn_open_file.setVisible(False)

        # Set Buttons state
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_resume.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        self.banner_msg.setText(f"Đang thực thi phiên làm việc [{self.current_job.job_id}]...")

        # Spawn worker
        self.worker = JobExecutionWorker(
            job_manager=self.job_manager,
            job_id=self.current_job.job_id,
            provider=provider,
            model=model,
            planner_provider=planner_provider,
            planner_model=planner_model,
            writer_provider=writer_provider,
            writer_model=writer_model,
            reviewer_provider=reviewer_provider,
            reviewer_model=reviewer_model,
        )
        self.worker.job_updated.connect(self._on_job_updated)
        self.worker.task_updated.connect(self._on_task_updated)
        self.worker.log_received.connect(self._on_log_received)
        self.worker.finished.connect(self._on_job_finished)
        self.worker.failed.connect(self._on_job_failed)
        self.worker.start()

    def _pause_job(self):
        if self.current_job:
            self.job_manager.pause_job(self.current_job.job_id)
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(True)
            self.stat_status.setText("TẠM DỪNG")
            self.stat_status.setStyleSheet(f"color: {STATUS_COLORS['PAUSED']}; font-weight: bold;")

    def _resume_job(self):
        if self.current_job:
            self.job_manager.resume_job(self.current_job.job_id)
            self.btn_pause.setEnabled(True)
            self.btn_resume.setEnabled(False)
            self.stat_status.setText("ĐANG CHẠY")
            self.stat_status.setStyleSheet(f"color: {STATUS_COLORS['RUNNING']}; font-weight: bold;")

    def _cancel_job(self):
        if self.current_job:
            self.job_manager.cancel_job(self.current_job.job_id)
            self.btn_cancel.setEnabled(False)
            self.btn_pause.setEnabled(False)
            self.btn_resume.setEnabled(False)
            self.btn_start.setEnabled(True)
            self.stat_status.setText("ĐÃ HỦY")
            self.stat_status.setStyleSheet(f"color: {STATUS_COLORS['CANCELLED']}; font-weight: bold;")

    def _on_job_updated(self, job: Job):
        self.current_job = job
        status_str = job.status.value
        color = STATUS_COLORS.get(status_str, "#F8FAFC")
        self.stat_status.setText(status_str)
        self.stat_status.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.stat_cost.setText(f"${job.total_cost_usd:.4f}")
        self.stat_tokens.setText(f"{job.total_tokens:,}")

    def _on_task_updated(self, task: Task):
        self.task_table.update_task(task)
        # Compute progress percentage
        if self.current_job and self.current_job.plan:
            all_tasks = self.job_manager.state_store.get_tasks_for_job(self.current_job.job_id)
            if all_tasks:
                succeeded = sum(1 for t in all_tasks if t.status == TaskStatus.SUCCEEDED)
                pct = int((succeeded / len(all_tasks)) * 100)
                self.progress_bar.setValue(pct)

    def _on_log_received(self, level: str, message: str, task_id: Optional[str]):
        self.log_viewer.append_log(level, message, task_id)

    def _on_job_finished(self, job: Job):
        self.current_job = job
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(False)
        self.btn_cancel.setEnabled(False)

        if job.status == JobStatus.SUCCEEDED:
            self.progress_bar.setValue(100)
            self.stat_status.setText("THÀNH CÔNG")
            self.stat_status.setStyleSheet(f"color: {STATUS_COLORS['SUCCEEDED']}; font-weight: bold;")

            msg = f"Tạo tài liệu thành công ({len(job.generated_files)} tệp). Thư mục: {Path(job.output_dir).name}"
            self.banner_msg.setText(msg)
            self.btn_open_folder.setVisible(True)

            docx_files = [f for f in job.generated_files if f.endswith(".docx")]
            if docx_files:
                self.btn_open_file.setVisible(True)

            QMessageBox.information(
                self, "Hoàn tất Xuất sắc",
                f"Đã tạo hoàn chỉnh tài liệu SOP và các tệp liên quan:\n" +
                "\n".join(f"• {Path(f).name}" for f in job.generated_files)
            )
        elif job.status == JobStatus.CANCELLED:
            self.banner_msg.setText("Công việc đã bị người dùng hủy bỏ.")
        else:
            self._on_job_failed(job.error_message or "Lỗi không xác định.")

    def _on_job_failed(self, error_message: str):
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_resume.setEnabled(False)
        self.btn_cancel.setEnabled(False)

        self.stat_status.setText("THẤT BẠI")
        self.stat_status.setStyleSheet(f"color: {STATUS_COLORS['FAILED']}; font-weight: bold;")
        self.banner_msg.setText(f"Lỗi: {error_message}")
        QMessageBox.critical(self, "Công việc Thất bại", f"Đã xảy ra lỗi trong quá trình thực thi:\n{error_message}")

    def _open_output_folder(self):
        if self.current_job and os.path.exists(self.current_job.output_dir):
            os.startfile(self.current_job.output_dir)

    def _open_output_file(self):
        if self.current_job:
            docx_files = [f for f in self.current_job.generated_files if f.endswith(".docx")]
            if docx_files and os.path.exists(docx_files[0]):
                os.startfile(docx_files[0])

    def _check_crash_recovery(self):
        recovered = self.job_manager.recover_crashed_jobs()
        if recovered:
            first = recovered[0]
            QMessageBox.information(
                self, "Khôi phục Phiên làm việc (Crash Recovery)",
                f"Phát hiện {len(recovered)} phiên làm việc bị gián đoạn đột ngột trước đó.\n"
                f"Phiên gần nhất [{first.job_id}] đã được phục hồi về trạng thái PAUSED trong cơ sở dữ liệu."
            )

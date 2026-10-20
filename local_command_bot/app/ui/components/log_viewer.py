"""Log Console Viewer Component."""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel
)
from PySide6.QtGui import QTextCursor

from app.security.sanitizer import mask_secrets


class LogViewer(QWidget):
    """Real-time formatted log viewer with search and auto-scroll."""

    LEVEL_COLORS = {
        "INFO": "#38BDF8",   # Sky blue
        "WARN": "#FBBF24",   # Amber
        "WARNING": "#FBBF24",
        "ERROR": "#F43F5E",  # Rose red
        "CRITICAL": "#E11D48",
        "DEBUG": "#94A3B8"   # Slate
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        lbl = QLabel("Nhật ký Thực thi (Live Logs):")
        lbl.setStyleSheet("font-weight: 600; color: #94A3B8;")
        toolbar.addWidget(lbl)

        toolbar.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Tìm kiếm log...")
        self.search_box.setMaximumWidth(200)
        self.search_box.textChanged.connect(self._filter_logs)
        toolbar.addWidget(self.search_box)

        btn_clear = QPushButton("Xóa log")
        btn_clear.clicked.connect(self.clear_logs)
        toolbar.addWidget(btn_clear)

        layout.addLayout(toolbar)

        # Text display
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet(
            "background-color: #0B1120; border: 1px solid #1E293B; "
            "font-family: 'Consolas', 'Courier New', monospace; font-size: 11.5px;"
        )
        layout.addWidget(self.text_area)

        self._all_log_entries: list[tuple[str, str, str, str | None]] = []

    def append_log(self, level: str, message: str, task_id: str | None = None) -> None:
        """Append a single log entry formatted with timestamp and level color."""
        time_str = datetime.now().strftime("%H:%M:%S")
        safe_msg = mask_secrets(message)
        self._all_log_entries.append((time_str, level.upper(), safe_msg, task_id))

        self._render_log_line(time_str, level.upper(), safe_msg, task_id)

    def _render_log_line(self, time_str: str, level: str, message: str, task_id: str | None) -> None:
        color = self.LEVEL_COLORS.get(level, "#E2E8F0")
        task_tag = f" <span style='color: #818CF8;'>[{task_id}]</span>" if task_id else ""
        html = (
            f"<div style='margin-bottom: 2px;'>"
            f"<span style='color: #64748B;'>[{time_str}]</span> "
            f"<span style='color: {color}; font-weight: bold;'>[{level}]</span>"
            f"{task_tag} "
            f"<span style='color: #F8FAFC;'>{message}</span>"
            f"</div>"
        )
        self.text_area.append(html)
        self.text_area.moveCursor(QTextCursor.MoveOperation.End)

    def _filter_logs(self, query: str):
        self.text_area.clear()
        q = query.strip().lower()
        for time_str, level, msg, task_id in self._all_log_entries:
            if not q or (q in msg.lower() or q in level.lower() or (task_id and q in task_id.lower())):
                self._render_log_line(time_str, level, msg, task_id)

    def clear_logs(self) -> None:
        self.text_area.clear()
        self._all_log_entries.clear()

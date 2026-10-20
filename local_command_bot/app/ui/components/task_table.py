"""Task Table UI Component for tracking DAG task execution in real-time."""

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QHBoxLayout, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.core.models import Task, TaskStatus
from app.ui.theme import STATUS_COLORS


class StatusBadge(QWidget):
    """Visual colored badge representing a task status."""

    def __init__(self, status: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        color_hex = STATUS_COLORS.get(status.upper(), "#64748B")
        label = QLabel(status.upper())
        label.setStyleSheet(
            f"background-color: {color_hex}; color: #FFFFFF; font-weight: bold; "
            f"font-size: 10px; border-radius: 4px; padding: 2px 8px;"
        )
        layout.addWidget(label)


class TaskTableWidget(QTableWidget):
    """Custom TableWidget displaying DAG tasks and live status updates."""

    COLUMNS = [
        "Mã Task",
        "Vai trò",
        "Tiêu đề Nhiệm vụ",
        "Provider / Model",
        "Trạng thái",
        "Lần thử",
        "Chi phí ($)",
        "Tokens"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)

        self._task_row_map: dict[str, int] = {}

    def set_tasks(self, tasks: list[Task]) -> None:
        """Populate the table with initial list of tasks."""
        self.setRowCount(len(tasks))
        self._task_row_map.clear()

        for row, task in enumerate(tasks):
            self._task_row_map[task.task_id] = row
            self._render_row(row, task)

    def update_task(self, task: Task) -> None:
        """Update or insert a single task in real-time."""
        if task.task_id in self._task_row_map:
            row = self._task_row_map[task.task_id]
        else:
            row = self.rowCount()
            self.insertRow(row)
            self._task_row_map[task.task_id] = row

        self._render_row(row, task)

    def _render_row(self, row: int, task: Task) -> None:
        title = task.input.get("title", task.task_id)

        # 0: Task ID
        id_item = QTableWidgetItem(task.task_id)
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, 0, id_item)

        # 1: Role
        role_label = task.role.value
        if task.role == TaskRole.PLANNER:
            role_label = "🎖️ CHỈ HUY"
        elif task.task_id == "T-FINAL":
            role_label = "🎖️ TỔNG HỢP"
        elif task.role == TaskRole.WRITER:
            role_label = "✍️ THỢ VIẾT"
        elif task.role == TaskRole.REVIEWER:
            role_label = "🔍 GIÁM SÁT"
        elif task.role == TaskRole.AUDITOR:
            role_label = "⚖️ KIỂM DUYỆT"

        role_item = QTableWidgetItem(role_label)
        role_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, 1, role_item)

        # 2: Title
        self.setItem(row, 2, QTableWidgetItem(title))

        # 3: Provider / Model
        prov_model = f"{task.provider} / {task.model}"
        self.setItem(row, 3, QTableWidgetItem(prov_model))

        # 4: Status Badge
        self.setCellWidget(row, 4, StatusBadge(task.status.value))

        # 5: Attempt
        attempt_item = QTableWidgetItem(f"{task.attempt_count}/{task.max_attempts}")
        attempt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, 5, attempt_item)

        # 6: Cost
        cost_item = QTableWidgetItem(f"${task.usage.estimated_cost_usd:.4f}")
        cost_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setItem(row, 6, cost_item)

        # 7: Tokens
        token_item = QTableWidgetItem(f"{task.usage.total_tokens:,}")
        token_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setItem(row, 7, token_item)

    def clear_tasks(self) -> None:
        """Clear all table rows."""
        self.setRowCount(0)
        self._task_row_map.clear()

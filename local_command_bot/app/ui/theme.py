"""Modern Dark Mode Theme and Stylesheet for PySide6 Desktop UI."""

DARK_STYLESHEET = """
/* =========================================================
   GLOBAL RESET & BASE STYLING
   ========================================================= */
QWidget {
    background-color: #0F172A; /* Deep Slate */
    color: #F8FAFC;            /* Clean White Text */
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Roboto", sans-serif;
    font-size: 13px;
    selection-background-color: #38BDF8;
    selection-color: #0F172A;
}

QMainWindow, QDialog {
    background-color: #0F172A;
}

/* =========================================================
   CARDS & CONTAINERS
   ========================================================= */
QFrame#card {
    background-color: #1E293B; /* Slate 800 */
    border: 1px solid #334155; /* Slate 700 */
    border-radius: 10px;
    padding: 12px;
}

QGroupBox {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 18px;
    padding-top: 14px;
    font-weight: 600;
    color: #38BDF8; /* Cyan accent */
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #1E293B;
    border-radius: 4px;
}

/* =========================================================
   INPUT CONTROLS
   ========================================================= */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 10px;
    color: #F8FAFC;
}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #38BDF8;
    background-color: #0B1120;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #1E293B;
    border: 1px solid #334155;
    selection-background-color: #0284C7;
    selection-color: #FFFFFF;
    color: #F8FAFC;
    padding: 4px;
}

/* =========================================================
   BUTTONS
   ========================================================= */
QPushButton {
    background-color: #334155;
    color: #F8FAFC;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #475569;
    border-color: #64748B;
}

QPushButton:pressed {
    background-color: #1E293B;
}

QPushButton:disabled {
    background-color: #1E293B;
    color: #64748B;
    border-color: #334155;
}

/* Primary Action Button (Start) */
QPushButton#primaryButton {
    background-color: #0284C7; /* Sky 600 */
    border: 1px solid #38BDF8;
    color: #FFFFFF;
}

QPushButton#primaryButton:hover {
    background-color: #0369A1;
    border-color: #7DD3FC;
}

QPushButton#primaryButton:pressed {
    background-color: #075985;
}

/* Danger Button (Cancel) */
QPushButton#dangerButton {
    background-color: #BE123C; /* Rose 700 */
    border: 1px solid #F43F5E;
    color: #FFFFFF;
}

QPushButton#dangerButton:hover {
    background-color: #9F1239;
}

/* Warning Button (Pause) */
QPushButton#warningButton {
    background-color: #D97706; /* Amber 600 */
    border: 1px solid #FBBF24;
    color: #FFFFFF;
}

QPushButton#warningButton:hover {
    background-color: #B45309;
}

/* Success Button (Resume / Open) */
QPushButton#successButton {
    background-color: #059669; /* Emerald 600 */
    border: 1px solid #34D399;
    color: #FFFFFF;
}

QPushButton#successButton:hover {
    background-color: #047857;
}

/* =========================================================
   TABLE VIEW
   ========================================================= */
QTableWidget {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    gridline-color: #1E293B;
    color: #E2E8F0;
    selection-background-color: #1E293B;
    selection-color: #38BDF8;
}

QHeaderView::section {
    background-color: #1E293B;
    color: #94A3B8;
    font-weight: 600;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #334155;
}

/* =========================================================
   PROGRESS BAR
   ========================================================= */
QProgressBar {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    color: #FFFFFF;
    font-weight: bold;
    height: 20px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #38BDF8);
    border-radius: 5px;
}

/* =========================================================
   SCROLLBARS
   ========================================================= */
QScrollBar:vertical {
    border: none;
    background-color: #0F172A;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #334155;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* =========================================================
   CHECKBOXES & LABELS
   ========================================================= */
QCheckBox {
    color: #E2E8F0;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #475569;
    border-radius: 4px;
    background-color: #0F172A;
}

QCheckBox::indicator:checked {
    background-color: #0284C7;
    border-color: #38BDF8;
}

QLabel {
    color: #E2E8F0;
}

QLabel#headerTitle {
    font-size: 18px;
    font-weight: 700;
    color: #38BDF8;
}

QLabel#statValue {
    font-size: 15px;
    font-weight: 700;
    color: #F8FAFC;
}

QLabel#statLabel {
    font-size: 11px;
    color: #94A3B8;
}
"""

STATUS_COLORS = {
    "PENDING": "#64748B",    # Slate
    "READY": "#0EA5E9",      # Sky
    "RUNNING": "#38BDF8",    # Cyan
    "SUCCEEDED": "#10B981",  # Emerald
    "FAILED": "#F43F5E",     # Rose
    "RETRYING": "#F59E0B",   # Amber
    "CANCELLED": "#94A3B8",  # Gray
    "PAUSED": "#F59E0B",     # Amber
    "PLANNING": "#A855F7",   # Purple
}
